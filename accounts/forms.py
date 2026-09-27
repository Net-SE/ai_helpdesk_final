from django.contrib.auth.forms import AuthenticationForm


class StyledAuthenticationForm(AuthenticationForm):
    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request=request, *args, **kwargs)

        self.fields["username"].widget.attrs.update(
            {
                "class": "form-control form-control-lg",
                "placeholder": "Enter username",
            }
        )
        self.fields["password"].widget.attrs.update(
            {
                "class": "form-control form-control-lg",
                "placeholder": "Enter password",
            }
        )
