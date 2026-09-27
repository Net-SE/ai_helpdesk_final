from django.contrib.auth.models import AbstractUser
from django.db import models

# Create your models here.


class User(AbstractUser):
    class Role(models.TextChoices):
        REQUESTER = "REQUESTER", "Requester"
        TECHNICIAN = "TECHNICIAN", "IT Technician"
        MANAGER = "MANAGER", "IT Manager"
        ADMIN = "ADMIN", "Administrator"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.REQUESTER)

    def is_it_staff(self) -> bool:
        return (
            self.role in {self.Role.TECHNICIAN, self.Role.MANAGER, self.Role.ADMIN}
            or self.is_superuser
        )

    def is_manager(self) -> bool:
        return self.role in {self.Role.MANAGER, self.Role.ADMIN} or self.is_superuser
