from fastapi import FastAPI, Form, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta
from sqlalchemy.orm import Session, joinedload
import models, string, random
from db import Base, engine, SessionLocal
from jwt import create_tok, decode_t

app = FastAPI(
    title="Dignity Bank",
    description="Provides you a secure and accessible account",
)


models.Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def generate_account_number():
    account_number = "23" + "".join(random.choices(string.digits, k=8))
    return account_number

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    user_id = decode_t(token)
    user = db.query(models.User).get(user_id)
    if not user:
        raise HTTPException(status_code=401, detail='Invalid user')
    return user



@app.get("/")
def ping():
    return {"message": "Dignity Active, Use /docs for testing"} 

# User registration endpoint
@app.post('/register')
def register(username: str = Form(...), password: str = Form(...), firstname: str = Form(...), lastname: str = Form(...), db: Session = Depends(get_db)):
    # Check if the username already exists in the database
    if db.query(models.User).filter(models.User.username == username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    # create the user
    user = models.User(username=username, password=password)
    # create account
    account = models.Account(
        user=user,
        account_number=generate_account_number(),
        first_name=firstname,
        last_name=lastname
    )
    # Add the user to the database

    db.add(user)
    db.add(account)
    db.commit()
    db.refresh(user)
    db.refresh(account)
    
    return {'message': 'User registered successfully', 'details': account}

# User login endpoint
@app.post('/login')
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not user.password == form_data.password:
        raise HTTPException(status_code=401, detail='Invalid login credentials')

    # Generate a JWT token
    access_token = create_tok(user)

    return {'access_token': access_token, 'token_type': 'bearer'}


# Deposit money endpoint
@app.post('/api/deposit')
def deposit(amount: float = Form(...), current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if amount <= 0:
        raise HTTPException(status_code=400, detail='Invalid deposit amount')

    # Retrieve the account associated with the current user
    account = db.query(models.Account).options(joinedload(models.Account.user)).filter(models.Account.user_id == current_user.id).first()

    if not account:
        raise HTTPException(status_code=404, detail='Account not found')

    # Update the account balance
    account.balance += amount
    db.commit()
    bal = account.balance

    return {'message': 'Deposit successful. Bal #' + str(bal) }

# Withdraw money endpoint
@app.post('/api/withdraw')
def withdraw(amount: float = Form(...), current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if amount <= 0:
        raise HTTPException(status_code=400, detail='Invalid withdrawal amount')

    # Retrieve the account associated with the current user
    account = db.query(models.Account).options(joinedload(models.Account.user)).filter(models.Account.user_id == current_user.id).first()

    if not account:
        raise HTTPException(status_code=404, detail='Account not found')

    if account.balance < amount:
        raise HTTPException(status_code=400, detail='Insufficient balance')

    # if account.user.pin != pin:
    #     raise HTTPException(status_code=401, detail='Invalid PIN')

    # Update the account balance
    account.balance -= amount
    db.commit()

    return {'message': 'Withdrawal successful'}

# Money transfer endpoint
@app.post('/api/transfer')
def transfer(recipient: str = Form(...), amount: float = Form(...), current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if amount <= 0:
        raise HTTPException(status_code=400, detail='Invalid transfer amount')

    # Retrieve the sender's account from the database
    sender_account = db.query(models.Account).filter(models.Account.user_id == current_user.id).first()

    if not sender_account:
        raise HTTPException(status_code=404, detail='Sender account not found')

    if sender_account.balance < amount:
        raise HTTPException(status_code=400, detail='Insufficient balance')

    # Retrieve the recipient's account from the database
    recipient_account = db.query(models.Account).filter(models.Account.account_number == recipient).first()

    if not recipient_account:
        raise HTTPException(status_code=404, detail='Recipient account not found')

    # Update the account balances
    sender_account.balance -= amount
    recipient_account.balance += amount
    db.commit()

    return {'message': 'Transfer successful'}

# Get all users endpoint
@app.get('/api/users')
def get_users(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Retrieve user data from the database
    users = db.query(models.User).all()

    # Prepare the response data
    user_data = []
    for user in users:
        account = db.query(models.Account).filter(models.Account.user_id == user.id).first()
        if account:
            user_info = {
                'username': user.username,
                'full_name': f"{account.first_name} {account.last_name}",
                'account_number': account.account_number,
                'balance': account.balance
            }
            user_data.append(user_info)

    return user_data
