import numpy as np
import decimal
from dataclasses import dataclass
import matplotlib.pyplot as plt
import csv

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
        self.monthly_payments = []
        self.loan_amounts = []
        self.investment_balances = []
        self.standard_deductions = []
        self.charitable_deductions = []
        self.salt_deductions = []
        self.mortgage_interest_deductions = []
        self.itemized_deductions = []
        self.deductions = []
        self.csv_rows = []
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
        self.monthly_payments = []
        self.loan_amounts = []
        self.investment_balances = []
        self.standard_deductions = []
        self.charitable_deductions = []
        self.salt_deductions = []
        self.mortgage_interest_deductions = []
        self.itemized_deductions = []
        self.deductions = []
        self.csv_rows = []
        self.investment_balance = 0
        self.loan_amount = self._INIT_LOAN_AMOUNT

    def get_income(self, year):
        return self.initial_income * (1+self.income_increase_rate)**year

    def get_living_expenses(self, year):
        return self.initial_living_expenses * (1+self.inflation_rate)**year

    def get_standard_deduction(self, year):
        # standard deduction is assumed to increase at inflation rate
        return self.initial_standard_deduction * (1+self.inflation_rate)**year

    def get_salt_deduction(self, income, year):
        # state and local tax (SALT) deduction
        # currently capped at $10k/year
        salt_cap = 10e3 * (1+self.inflation_rate)**year
        return min(salt_cap, self.get_state_tax(income))

    def get_mortgage_interest_deduction(self, mortgage_balance, annual_mortgage_interest):
        return min(750e3, mortgage_balance)/mortgage_balance * annual_mortgage_interest

    def get_current_tax_brackets(self, year):
        # tax brackets are assumed to increase at inflation rate
        current_tax_brackets = [(income_level * (1+self.inflation_rate)**year, tax_rate) for \
                                (income_level, tax_rate) in self.initial_tax_brackets]
        return current_tax_brackets

    def get_state_tax(self, income):
        # IL state tax is a flat rate with some income exempted
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
            interest_payment = self.interest_rate/12 * self.loan_amount
            principal_payment = self.monthly_payment - interest_payment
            monthly_payment = self.monthly_payment
            self.loan_amount = self.loan_amount - principal_payment
            self.interest_payments.append(interest_payment)
            self.principal_payments.append(principal_payment)
            self.monthly_payments.append(monthly_payment)
        else:
            self.interest_payments.append(0)
            self.principal_payments.append(0)
            self.monthly_payments.append(0)
            
        self.loan_amounts.append(self.loan_amount)
        
    def step_year(self):
        for _ in range(12):
            self.step_month()

        annual_mortgage_interest = sum(self.interest_payments[-12:])
        annual_mortgage_payments = sum(self.monthly_payments[-12:])
        
        annual_income = self.get_income(self.time_years)
        standard_deduction = self.get_standard_deduction(self.time_years)

        charitable_deduction = annual_income * self.charitable_contribution_percent
        salt_deduction = self.get_salt_deduction(annual_income, self.time_years)
        mortgage_interest_deduction = self.get_mortgage_interest_deduction(self.loan_amount, annual_mortgage_interest)
        itemized_deduction = charitable_deduction + salt_deduction + mortgage_interest_deduction

        deduction = max(standard_deduction, itemized_deduction)
        state_tax = self.get_state_tax(annual_income)
        federal_tax = self.get_federal_tax(annual_income - deduction, self.time_years)
        living_expenses = self.get_living_expenses(self.time_years)

        investment_amount = annual_income - living_expenses - state_tax - federal_tax - annual_mortgage_payments
        self.investment_balance = self.investment_balance*(1+self.investment_return_rate) + investment_amount
        decimal_investment_balance = '{0:.3E}'.format(decimal.Decimal(self.investment_balance))

        self.standard_deductions.append(standard_deduction)
        self.charitable_deductions.append(charitable_deduction)
        self.salt_deductions.append(salt_deduction)
        self.mortgage_interest_deductions.append(mortgage_interest_deduction)
        self.itemized_deductions.append(itemized_deduction)
        self.deductions.append(deduction)
        self.investment_balances.append(self.investment_balance)

        self.csv_rows.append({
            'TimeYears': self.time_years,
            'LoanBalance': self.loan_amount,
            'Income': annual_income, 
            'AnnualTotalMortgagePayments': annual_mortgage_payments, 
            'LivingExpenses': living_expenses, 
            'StateTax': state_tax, 
            'StandardDeduction': standard_deduction, 
            'CharitableDeduction': charitable_deduction, 
            'SALTDeduction': salt_deduction, 
            'MortgageInterestDeduction': mortgage_interest_deduction, 
            'PreferredDeduction': deduction, 
            'FederalTax': federal_tax, 
            'InvestmentAmount': investment_amount, 
            'InvestmentBalance': self.investment_balance
            })
        
        self.time_years += 1
        print(self.time_years, self.loan_amount, deduction, investment_amount, decimal_investment_balance)

    def run(self):
        self.monthly_payment = self.loan_amount * \
                               (self.interest_rate/12 * (1 + self.interest_rate/12) ** (self.mortgage_years*12)) / \
                               ((1 + self.interest_rate/12) ** (self.mortgage_years*12) - 1)
        
        for _ in range(self.sim_years):
            self.step_year()

        with open(f'mortgage_{self.mortgage_years}_years_{self.investment_return_rate}_arr.csv', 'w', newline='') as csvfile:
            fieldnames = [
                'TimeYears',
                'LoanBalance',
                'Income',
                'AnnualTotalMortgagePayments',
                'LivingExpenses',
                'StateTax',
                'StandardDeduction',
                'CharitableDeduction',
                'SALTDeduction',
                'MortgageInterestDeduction',
                'PreferredDeduction',
                'FederalTax',
                'InvestmentAmount',
                'InvestmentBalance'
            ]
            csvwriter = csv.DictWriter(csvfile, fieldnames=fieldnames)
            csvwriter.writeheader()
            csvwriter.writerows(self.csv_rows)

        # plt.plot(range(self.sim_years), self.loan_amounts[::12], label="loan balance")
        # plt.plot(range(self.sim_years), self.investment_balances, label= "investment balance")
        # plt.legend(loc="upper left")
        # plt.show()

        # plt.plot(range(self.sim_years), self.standard_deductions, label="standard deduction")
        # plt.plot(range(self.sim_years), self.charitable_deductions, label= "charitable deduction")
        # plt.plot(range(self.sim_years), self.salt_deductions, label= "SALT deduction")
        # plt.plot(range(self.sim_years), self.mortgage_interest_deductions, label= "mortgage interest deduction")
        # plt.plot(range(self.sim_years), self.itemized_deductions, label= "itemized deduction")
        # plt.legend(loc="upper left")
        # plt.show()

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

for mortgage_length in [15, 30]:
    for arr in [0.03, 0.05, 0.07]:
        sim.restart()
        sim.mortgage_years = mortgage_length
        sim.investment_return_rate = arr
        sim.run()