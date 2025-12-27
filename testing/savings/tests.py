from django.test import TestCase
from django.contrib.auth import get_user_model
from datetime import date, timedelta
from decimal import Decimal
from savings.models import SavingsGoal, SurplusTracker
from savings.utils import surplus_rollover

User = get_user_model()

class SurplusRolloverTests(TestCase):

    def setUp(self):
  
        self.user = User.objects.create_user(username="testuser", password="password123")

    def test_current_month_rollover_to_multiple_goals(self):
        today = date.today()

       
        g1 = SavingsGoal.objects.create(
            user=self.user, name="G1", target_amount=Decimal("2000"), current_amount=Decimal("2000"), deadline=today + timedelta(days=30)
        )

        g2 = SavingsGoal.objects.create(
            user=self.user, name="G2", target_amount=Decimal("5000"), current_amount=Decimal("4000"), deadline=today + timedelta(days=30)
        )
       
        g3 = SavingsGoal.objects.create(
            user=self.user, name="G3", target_amount=Decimal("3000"), current_amount=Decimal("0"), deadline=today + timedelta(days=30)
        )

       
        tracker = SurplusTracker.objects.create(user=self.user, last_surplus=Decimal("0"))
        current_month_balance = Decimal("2000")

        balances = surplus_rollover(self.user, excess_amount=current_month_balance)

        g1.refresh_from_db()
        g2.refresh_from_db()
        g3.refresh_from_db()
        tracker.refresh_from_db()


        # G1 still complete
        self.assertEqual(g1.current_amount, Decimal("2000"))

        # G2 fully completed (4000 + 1000)
        self.assertEqual(g2.current_amount, Decimal("5000"))

        # G3 gets remaining 1000 (still incomplete)
        self.assertEqual(g3.current_amount, Decimal("1000"))

        # No balance left after allocation
        self.assertEqual(tracker.last_surplus, Decimal("0"))

        # Current month resets to 0
        self.assertEqual(balances["current_balance"], Decimal("0"))

        print("Test Passed: Surplus rollover correctly allocated across multiple goals.")