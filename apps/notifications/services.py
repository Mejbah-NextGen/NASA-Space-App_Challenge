from .models import Notification


def create_notification(user, *, kind=Notification.Kind.SYSTEM, title, body="", target_url=""):
    if not user:
        return None
    if kind not in Notification.Kind.values:
        kind = Notification.Kind.SYSTEM
    return Notification.objects.create(
        user=user,
        kind=kind,
        title=title[:180],
        body=body[:1000],
        target_url=target_url[:500],
    )
