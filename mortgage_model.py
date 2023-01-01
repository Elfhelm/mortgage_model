import numpy as np
import decimal
from dataclasses import dataclass
import matplotlib.pyplot as plt

@dataclass
class MortgageSim:
    home_price:                 int
    down_payment:               int    # mortgage size = home price - down payment
    sim_years:                  int    # length of time to simulate
    mortgage_years:             int    # length of mortgage
    initial_income:             int    # income in first year
    initial_living_expenses:    int
    initial_standard_deduction: int    # standard deduction increases with inflation
    income_increase_rate:       float  # percentage rate at which income increases
    inflation_rate:             float  # percentage rate at which standard deduction and tax brackets increase
    interest_rate:              float  # for mortgage
    investment_return_rate:     float  # assumed rate of return for other investments
    charitable_contribution_percent: float  # percentage of annual income donated to charity

    def __post_init__(self):
        self.time_years = 0
        self.interest_payments = []
        self.principal_payments = []
        self.loan_amounts = []
        self.investment_balances = []
        self.initial_tax_brackets = [
            (22000, 0.1),
            (89450, 0.12),
            (190750, 0.22),
            (364200, 0.24),
            (462500, 0.32),
            (693750, 0.35),
            (np.inf, 0.37),
            ]
        self.loan_amount = self.home_price - self.down_payment
        self._INIT_LOAN_AMOUNT = self.loan_amount
        self.investment_balance = 0

    def restart(self):
        self.time_years = 0
        self.interest_payments = []
        self.principal_payments = []
        self.loan_amounts = []
        self.investment_balances = []
        self.investment_balance = 0
        self.loan_amount = self._INIT_LOAN_AMOUNT

    def get_income(self, year):
        return self.initial_income * (1+self.income_increase_rate)**year

    def get_living_expenses(self, year):
        return self.initial_living_expenses * (1+self.inflation_rate)**year

    def get_standard_deduction(self, year):
        # standard deduction is assumed to increase at inflation rate
        return self.initial_standard_deduction * (1+self.inflation_rate)**year

    def get_salt_deduction(self, income):
        # state and local tax (SALT) deduction
        # capped at $10k/year
        return min(10e3, self.get_state_tax(income))

    def get_mortgage_interest_deduction(self, mortgage_balance, annual_mortgage_interest):
        return min(750e3, mortgage_balance)/mortgage_balance * annual_mortgage_interest

    def get_current_tax_brackets(self, year):
        # tax brackets are assumed to increase at inflation rate
        current_tax_brackets = [(income_level * (1+self.inflation_rate)**year, tax_rate) for \
                                (income_level, tax_rate) in self.initial_tax_brackets]
        return current_tax_brackets

    def get_state_tax(self, income):
        exemptions = 2425*2
        return (income-exemptions) * 0.0495

    def get_federal_tax(self, income, year):
        current_tax_brackets = self.get_current_tax_brackets(year)
        total_tax = 0
        prev_income_level = 0
        for income_level, tax_rate in current_tax_brackets:
            if income >= income_level:
                total_tax += (income_level - prev_income_level) * tax_rate
            else:
                total_tax += (income - prev_income_level) * tax_rate
                break
            prev_income_level = income_level

        return total_tax

    def step_month(self):
        if self.time_years < self.mortgage_years:
            interest_payment = sim.interest_rate/12 * sim.loan_amount
            principal_payment = sim.monthly_payment - interest_payment
            self.loan_amount = self.loan_amount - principal_payment
            self.interest_payments.append(interest_payment)
            self.principal_payments.append(principal_payment)
        else:
            self.interest_payments.append(0)
            self.principal_payments.append(0)
            
        self.loan_amounts.append(self.loan_amount)
        
    def step_year(self):
        for _ in range(12):
            self.step_month()

        annual_mortgage_interest = sum(self.interest_payments[-12:])
        annual_mortgage_payments = self.monthly_payment * 12
        
        annual_income = self.get_income(self.time_years)
        standard_deduction = self.get_standard_deduction(self.time_years)

        charitable_deduction = annual_income * self.charitable_contribution_percent
        salt_deduction = self.get_salt_deduction(annual_income)
        mortgage_interest_deduction = self.get_mortgage_interest_deduction(self.loan_amount, annual_mortgage_interest)
        itemized_deduction = charitable_deduction + salt_deduction + mortgage_interest_deduction

        deduction = max(standard_deduction, itemized_deduction)
        state_tax = self.get_state_tax(annual_income)
        federal_tax = self.get_federal_tax(annual_income - deduction, self.time_years)

        investment_amount = annual_income - self.get_living_expenses(self.time_years) - state_tax - federal_tax - annual_mortgage_payments
        self.investment_balance = self.investment_balance*(1+self.investment_return_rate) + investment_amount
        self.investment_balances.append(self.investment_balance)
        decimal_investment_balance = '{0:.3E}'.format(decimal.Decimal(self.investment_balance))
        
        self.time_years += 1
        print(self.time_years, self.loan_amount, deduction, investment_amount, decimal_investment_balance)

    def run(self):
        self.monthly_payment = self.loan_amount * \
                               (self.interest_rate/12 * (1 + self.interest_rate/12) ** (self.mortgage_years*12)) / \
                               ((1 + self.interest_rate/12) ** (self.mortgage_years*12) - 1)
        
        for _ in range(self.sim_years):
            self.step_year()

        plt.plot(range(self.sim_years), self.loan_amounts[::12], label="loan balance")
        plt.plot(range(self.sim_years), self.investment_balances, label= "investment balance")
        plt.legend(loc="upper left")
        plt.show()

sim = MortgageSim(
    home_price = 1.2e6,
    down_payment = 400e3,
    sim_years = 30,
    mortgage_years = 15,
    interest_rate = 0.06,
    initial_income = 500e3,
    initial_living_expenses = 100e3,
    income_increase_rate = 0.02,
    charitable_contribution_percent = 0.05,
    initial_standard_deduction = 25900,
    inflation_rate = 0.02,
    investment_return_rate = 0.03,
    )

sim.run()

sim.restart()
sim.mortgage_years = 30
sim.run()
