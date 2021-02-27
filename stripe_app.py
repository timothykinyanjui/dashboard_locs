import stripe
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import streamlit as st

# Distinguisghes the names and name
def distinguish(x,y):
    return x if x == x else y

# Load data function
@st.cache
def load_data(user_input:str) -> pd.DataFrame:
    # Set stripe API key
    stripe.api_key = user_input

    # Retrieve balance transactions (all payments by customers, payouts, fees and refunds)
    bal_trans = stripe.BalanceTransaction.list(limit = 3)

    # Loop to get all balance transcations
    data = pd.DataFrame()

    for bal_iter in bal_trans.auto_paging_iter():

        # Get the data in pandas frame
        data_temp = pd.json_normalize(bal_iter)[["id","object","amount","description","fee","net","reporting_category","status","type","created"]]
        data = data.append(data_temp)

    # Create readable date from unix time
    data = data.assign(date = lambda x: x['created'].apply(lambda x: pd.to_datetime(x, unit = 's', utc = True)))

    # Get charges data with customer names
    charges = stripe.Charge.list(limit = 3)

    # Loop to get all balance transcations
    dataCharge = pd.DataFrame()

    for char_iter in charges.auto_paging_iter():
        
        # Get the data in pandas frame
        names = char_iter["billing_details"]["name"]
        t_id = char_iter["balance_transaction"]
        c_id = char_iter['id']
        email = char_iter['receipt_email']
        dataCharge = dataCharge.append(pd.DataFrame({'id': t_id, 'name': names, 'email':email}, index = [0]))

    temp_data = dataCharge.groupby('email', as_index = False).agg(names = ('name','first'))

    # Get the unique names (still duplicated in email exist)
    dataChargeT = dataCharge.merge(temp_data, on = 'email', how = 'left').assign(name = lambda x: x.apply(lambda y: distinguish(y['names'], y['name']), axis = 1))

    # Join the customer data
    dataAll = data.merge(dataChargeT, on = 'id', how = 'left')
    
    return dataAll

# Use a wide page rather than center
st.set_page_config(layout="wide")

# Title for the app
st.title(f"Beth's Sisterlocs dashboard")

# Input text
st.sidebar.header("Enter text")
user_input = st.sidebar.text_input("Enter text")

# Select dates
st.sidebar.header("Select dates of interest")

# Start date
max_date = datetime.now().date()
d1 = st.sidebar.date_input('start date', min_value = datetime(2020,6,20).date(),  max_value = max_date, value = datetime(2020,6,20))

# End date
d2 = st.sidebar.date_input('end date', min_value = d1, max_value = max_date, value = max_date)


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

st.sidebar.header("Select customer")
xx = list(set(dataAll.sort_values('name',ascending = False).query("name == name")['name'].to_list()))
xx.sort()
selection_customers = ['All'] + xx
customer_selectbox = st.sidebar.selectbox("Select customer", selection_customers)


if customer_selectbox == "All":
    charge_data = charge_data
    
else:
    charge_data = charge_data.query("name == @customer_selectbox")

# Organise the columns
col1, col2 = st.beta_columns(2)

# Plot the gross income
gross = charge_data.query("reporting_category == 'charge'").assign(datee = lambda x: x['date'].apply(lambda y: datetime(y.year, y.month,1))).groupby('datee', as_index = False)\
        .agg(total = ('amount','sum'))
plt.figure(num = 'fig1', figsize=(10, 5))
plt.plot(gross['datee'], gross['total'],'.-')

# Plot the net income
net = charge_data.query("reporting_category == 'charge' or reporting_category == 'refund'")\
        .assign(datee = lambda x: x['date'].apply(lambda y: datetime(y.year, y.month,1)))\
        .groupby('datee', as_index = False)\
        .agg(charge_amt = ('net','sum'))

total_payments = charge_data.query("reporting_category == 'charge'")\
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
st.write(charge_data[["date",'name',"description","amount","fee","net","type"]])