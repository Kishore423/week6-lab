class DuckFine:
    """Late fees for the QuackLoan rubber-duck lending library."""

    DAILY_FEE = 0.50 # dollars per chargeable day
    GRACE_DAYS = 2 # the first two days late are forgiven
    #MAX_FEE = 5.00 # a single fine never exceeds this

    def __init__(self, member_id):
        self.member_id = member_id
        self.total_owed = 0.0
    def charge(self, days_late, deluxe=False):
        if days_late < 0:
            raise ValueError("days_late must not be negative")
        chargeable = max(0, days_late - self.GRACE_DAYS) # calculates number of chargable days
        fee = chargeable * self.DAILY_FEE
        if deluxe:
            fee *= 2
        fee = min(fee, self.MAX_FEE)
        self.total_owed += fee
        return fee
