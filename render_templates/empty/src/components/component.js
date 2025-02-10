import './style.css';
import React, { useState } from 'react';

const Dashboard = () => {
  const [budget, setBudget] = useState({
    income: 3000,
    expenses: [
      { category: 'groceries', amount: 400 },
      { category: 'utilities', amount: 200 },
      { category: 'entertainment', amount: 150 },
      { category: 'savings', amount: 500 },
    ],
  });

  const [expenses, setExpenses] = useState([
    { date: '2023-10-10', category: 'groceries', amount: 50 },
    { date: '2023-10-11', category: 'entertainment', amount: 30 },
  ]);

  const [savings, setSavings] = useState({
    goal: 5000,
    saved: 1200,
  });

  const addExpense = (category, amount) => {
    const newExpense = { date: new Date().toISOString().split('T')[0], category, amount };
    setExpenses([...expenses, newExpense]);
  };

  const calculateBudget = () => {
    const totalExpenses = budget.expenses.reduce((sum, expense) => sum + expense.amount, 0);
    return budget.income - totalExpenses;
  };

  const calculateProgress = () => {
    return (savings.saved / savings.goal) * 100;
  };

  return (
    <div className="dashboard">
      <div className="budget-planner">
        <h2>Monthly Budget Planner</h2>
        {budget.expenses.map((expense, index) => (
          <p key={index}>
            <strong>{expense.category}:</strong> ${expense.amount}
          </p>
        ))}
        <p>
          <strong>Savings:</strong> ${calculateBudget()}
        </p>
      </div>
      <div className="expense-tracker">
        <h2>Expense Tracker</h2>
        {expenses.map((expense, index) => (
          <p key={index}>
            <strong>{expense.date}</strong> - {expense.category}: ${expense.amount}
          </p>
        ))}
        <button onClick={() => addExpense('groceries', 25)}>Add $25 to Groceries</button>
      </div>
      <div className="savings-goal">
        <h2>Savings Goal</h2>
        <div className="progress-bar">
          <div className="progress" style={{ width: `${calculateProgress()}%` }}></div>
        </div>
        <p className="label">
          <strong>{calculateProgress().toFixed(2)}%</strong>
        </p>
        <p className="label">
          <strong>Goal:</strong> ${savings.goal}
        </p>
        <p className="label">
          <strong>Saved:</strong> ${savings.saved}
        </p>
      </div>
    </div>
  );
};

export default Dashboard;