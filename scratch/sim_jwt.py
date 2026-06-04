from jose import jwt

def get_error(d):
    try:
        t = jwt.encode(d, 'secret', algorithm='HS256')
        jwt.decode(t, 'secret', algorithms=['HS256'])
    except Exception as e:
        print("Error with dict", d, ":", type(e), e)

get_error({"exp": "string"})
get_error({"aud": 123})
get_error({"iss": 123})
