import stripe
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import streamlit as st

# Load data function
#stripe_key = "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"

@st.cache
def load_data(user_input:str) -> pd.DataFrame:
    # Set stripe API key
    stripe.api_key = user_input

    # Retrieve balance transactions (all payments by customers, payouts, fees and refunds)
    bal_trans = stripe.BalanceTransaction.list(limit=3)

    # Loop to get all balance transcations
    data = pd.DataFrame()

    for bal_iter in bal_trans.auto_paging_iter():

        # Get the data in pandas frame
        data_temp = pd.json_normalize(bal_iter)[["id","object","amount","description","fee","net","reporting_category","status","type","created"]]
        data = data.append(data_temp)

    # Create readable date from unix time
    data = data.assign(date = lambda x: x['created'].apply(lambda x: pd.to_datetime(x, unit = 's', utc = True)))
    
    return data

# Use a wide page rather than center
st.set_page_config(layout="wide")

# Title for the app
st.title(f"Beth's Sisterlocs dashboard")

# Input text
st.sidebar.header("Enter text")
user_input = st.sidebar.text_input("Enter text")

st.sidebar.header("Select dates of interest")
d1 = st.sidebar.date_input('start date', min_value = datetime(2020,6,20).date(),  max_value = datetime.now().date(), value = datetime(2020,6,20))
d2 = st.sidebar.date_input('end date', min_value = datetime(2020,6,20), max_value = datetime.now().date(), value = datetime.now().date())

# Just show some data
st.spinner(text='Loading the data ...')
data = load_data(user_input)
dataAll = data\
        .assign(amount = lambda x: x['amount'].apply(lambda y: round(y/100,2)),
                fee = lambda x: x['fee'].apply(lambda y: round(y/100,2)),
               net = lambda x: x['net'].apply(lambda y: round(y/100,2)),
               datee = lambda x: x['date'].apply(lambda y: y.date))\
        .query("datee >= @d1 and datee <= @d2")

# A checkbox to determine what to show
st.sidebar.header("Select data")
add_selectbox = st.sidebar.selectbox(
    "Select data to show?",
    ("All", "Charge", "Payout", "Refunds")
)

if add_selectbox == "Charge":
    charge_data = dataAll.query("type == 'charge'")
    
elif add_selectbox == "Payout":
    charge_data = dataAll.query("type == 'payout'")
    
elif add_selectbox == "Refunds":
    charge_data = dataAll.query("type == 'refund'")
    
else:
    charge_data = dataAll


# Organise the columns
col1, col2 = st.beta_columns(2)

# Plot the gross income
gross = dataAll.query("reporting_category == 'charge'").assign(datee = lambda x: x['date'].apply(lambda y: datetime(y.year, y.month,1))).groupby('datee', as_index = False)\
        .agg(total = ('amount','sum'))
plt.figure(num = 'fig1', figsize=(10, 5))
plt.plot(gross['datee'], gross['total'],'.-')

# Plot the net income
net = dataAll.query("reporting_category == 'charge' or reporting_category == 'refund'")\
        .assign(datee = lambda x: x['date'].apply(lambda y: datetime(y.year, y.month,1)))\
        .groupby('datee', as_index = False)\
        .agg(charge_amt = ('net','sum'))

total_payments = dataAll.query("reporting_category == 'charge'")\
        .assign(datee = lambda x: x['date'].apply(lambda y: datetime(y.year, y.month,1)))\
        .groupby('datee', as_index = False)\
        .agg(payments = ('net','count'))

plt.figure(num = 'fig2', figsize=(10, 5))
plt.plot(total_payments['datee'], total_payments['payments'],'.-')

# Two columns
col1.subheader(f"Total: £ {round(gross['total'].sum(),2)}. Net: £ {round(net['charge_amt'].sum(),2)}")
col2.subheader(f"Total number of payments: {total_payments['payments'].sum()}")
col1.pyplot(plt.figure(num = 'fig1'))
col2.pyplot(plt.figure(num = 'fig2'))

st.subheader('Transaction data')
st.write(charge_data[["date","description","amount","fee","net","type"]])