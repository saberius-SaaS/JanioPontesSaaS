from jose import jwt
from datetime import datetime, timedelta, timezone

t = jwt.encode("foo", "secret", algorithm="HS256")
try:
    print("decoding string payload...")
    print(jwt.decode(t, "secret", algorithms=["HS256"]))
except Exception as e:
    print("Error:", type(e), e)

t2 = jwt.encode({"exp": datetime.now(timezone.utc)+timedelta(days=1), "cliente": "foo"}, "secret", algorithm="HS256")
try:
    print("decoding dict payload...")
    jwt.decode(t2, "secret", algorithms=["HS256"])
except Exception as e:
    print("Error:", type(e), e)
