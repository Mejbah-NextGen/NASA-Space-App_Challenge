from django.core import signing


SIGNING_SALT = "farm-time-machine-email-verification"


def create_verification_token(user):
    return signing.dumps({"user_id": user.pk, "email": user.email}, salt=SIGNING_SALT, compress=True)


def read_verification_token(token, max_age):
    return signing.loads(token, salt=SIGNING_SALT, max_age=max_age)
