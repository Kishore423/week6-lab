import unittest

from duckfine import DuckFine


class TestDuckFineInit(unittest.TestCase):
    # Checks the constructor sets up a member's starting state.

    def test_stores_member_id(self):
        # The id passed in is kept on the object as-is.
        fine = DuckFine("M001")
        self.assertEqual(fine.member_id, "M001")

    def test_new_member_owes_nothing(self):
        # A brand-new member starts with a clean slate, not None or 0 (int).
        fine = DuckFine("M001")
        self.assertEqual(fine.total_owed, 0.0)


class TestDuckFineValidation(unittest.TestCase):
    # Checks charge() rejects impossible input instead of silently accepting it.

    def setUp(self):
        self.fine = DuckFine("M001")

    def test_negative_days_raises_value_error(self):
        # You cannot return a duck before you borrowed it -> ValueError.
        with self.assertRaises(ValueError):
            self.fine.charge(-1)

    def test_negative_days_does_not_change_total_owed(self):
        # The rejected call must leave no side effect on the running total.
        with self.assertRaises(ValueError):
            self.fine.charge(-1)
        self.assertEqual(self.fine.total_owed, 0.0)


class TestDuckFineGracePeriod(unittest.TestCase):
    # Checks the first GRACE_DAYS (2) days late are free. Lower boundary of the fee.

    def setUp(self):
        self.fine = DuckFine("M001")

    def test_zero_days_late_is_free(self):
        # Returned on time -> no fee at all.
        self.assertAlmostEqual(self.fine.charge(0), 0.0)

    def test_one_day_late_is_forgiven(self):
        # Inside the grace window -> still free.
        self.assertAlmostEqual(self.fine.charge(1), 0.0)

    def test_last_grace_day_is_forgiven(self):
        # BOUNDARY: day 2 is the last forgiven day, so it must still be $0.00.
        self.assertAlmostEqual(self.fine.charge(2), 0.0)


class TestDuckFineStandardFee(unittest.TestCase):
    # Checks the normal (non-deluxe) fee maths and the MAX_FEE ceiling.

    def setUp(self):
        self.fine = DuckFine("M001")

    def test_first_day_after_grace_charges_one_daily_fee(self):
        # BOUNDARY: day 3 is the first chargeable day -> exactly one DAILY_FEE.
        self.assertAlmostEqual(self.fine.charge(3), 0.50)

    def test_fee_is_daily_rate_times_chargeable_days(self):
        # 6 days late - 2 grace = 4 chargeable days x $0.50 = $2.00.
        self.assertAlmostEqual(self.fine.charge(6), 2.00)

    def test_fee_just_below_cap(self):
        # BOUNDARY: 11 days -> 9 chargeable -> $4.50, just below MAX_FEE.
        self.assertAlmostEqual(self.fine.charge(11), 4.50)

    def test_fee_exactly_at_cap_is_not_reduced(self):
        # BOUNDARY: 12 days -> 10 chargeable -> $5.00, exactly MAX_FEE.
        # Catches an off-by-one cap that would wrongly trim a fee landing on the limit.
        self.assertAlmostEqual(self.fine.charge(12), 5.00)

    def test_fee_above_cap_is_capped(self):
        # BOUNDARY: 13 days -> $5.50 uncapped, so the cap must pull it back to $5.00.
        self.assertAlmostEqual(self.fine.charge(13), 5.00)

    def test_very_late_fee_is_capped(self):
        # An absurd delay still cannot exceed MAX_FEE.
        self.assertAlmostEqual(self.fine.charge(1000), 5.00)


class TestDuckFineDeluxe(unittest.TestCase):
    # Checks the deluxe flag, which doubles the fee BEFORE the cap is applied.

    def setUp(self):
        self.fine = DuckFine("M001")

    def test_deluxe_doubles_the_fee(self):
        # 5 days -> 3 chargeable -> $1.50, doubled -> $3.00 (still under the cap).
        self.assertAlmostEqual(self.fine.charge(5, deluxe=True), 3.00)

    def test_deluxe_within_grace_is_still_free(self):
        # Doubling zero is still zero, so grace beats the deluxe surcharge.
        self.assertAlmostEqual(self.fine.charge(2, deluxe=True), 0.0)

    def test_deluxe_fee_just_below_cap(self):
        # BOUNDARY: 6 days -> 4 chargeable -> $2.00, doubled -> $4.00.
        self.assertAlmostEqual(self.fine.charge(6, deluxe=True), 4.00)

    def test_deluxe_fee_exactly_at_cap_is_not_reduced(self):
        # BOUNDARY: 7 days -> 5 chargeable -> $2.50, doubled -> exactly $5.00.
        self.assertAlmostEqual(self.fine.charge(7, deluxe=True), 5.00)

    def test_deluxe_fee_above_cap_is_capped(self):
        # 8 days -> $3.00 doubled = $6.00, capped back down to $5.00.
        # Proves the cap is applied AFTER doubling, not before.
        self.assertAlmostEqual(self.fine.charge(8, deluxe=True), 5.00)

    def test_deluxe_defaults_to_false(self):
        # Same 5 days without the flag -> the undoubled $1.50.
        self.assertAlmostEqual(self.fine.charge(5), 1.50)


class TestDuckFineTotalOwed(unittest.TestCase):
    # Checks the running balance accumulates correctly across many charges.

    def setUp(self):
        self.fine = DuckFine("M001")

    def test_charge_adds_fee_to_total_owed(self):
        # The value returned by charge() is the same value added to the balance.
        fee = self.fine.charge(4)
        self.assertAlmostEqual(self.fine.total_owed, fee)

    def test_total_owed_accumulates_across_charges(self):
        # Two separate fines add up: $0.50 + $2.00 = $2.50.
        self.fine.charge(3)
        self.fine.charge(6)
        self.assertAlmostEqual(self.fine.total_owed, 2.50)

    def test_forgiven_charge_does_not_increase_total_owed(self):
        # A $0.00 fine must not nudge the balance.
        self.fine.charge(2)
        self.assertAlmostEqual(self.fine.total_owed, 0.0)

    def test_cap_applies_per_fine_not_to_total_owed(self):
        # MAX_FEE limits each SINGLE fine, so two capped fines total $10.00, not $5.00.
        self.fine.charge(20)
        self.fine.charge(20)
        self.assertAlmostEqual(self.fine.total_owed, 10.00)

    def test_members_have_independent_totals(self):
        # Charging one member must not touch another member's balance.
        other = DuckFine("M002")
        self.fine.charge(6)
        self.assertAlmostEqual(other.total_owed, 0.0)


if __name__ == "__main__":
    unittest.main()
