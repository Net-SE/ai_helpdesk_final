from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from knowledgebase.models import KBArticle
from tickets.models import SLAConfig, Ticket

User = get_user_model()


class Command(BaseCommand):
    help = "Seed demo users, SLA rules, three KB articles, and sample tickets."

    def handle(self, *args, **options):
        self.seed_sla_rules()

        admin = self.upsert_user(
            username="admin",
            email="admin@example.com",
            role="ADMIN",
            password="Password123!",
            is_staff=True,
            is_superuser=True,
        )

        manager = self.upsert_user(
            username="manager",
            email="manager@example.com",
            role="MANAGER",
            password="Password123!",
        )

        technician = self.upsert_user(
            username="tech1",
            email="tech1@example.com",
            role="TECHNICIAN",
            password="Password123!",
        )

        requester = self.upsert_user(
            username="req1",
            email="req1@example.com",
            role="REQUESTER",
            password="Password123!",
        )

        self.create_ai_bot()
        self.seed_knowledge_base(technician)
        self.seed_tickets(requester, technician)

        self.stdout.write(self.style.SUCCESS("Demo data seeded successfully."))
        self.stdout.write("Demo logins (local development only):")
        self.stdout.write("  admin / Password123!")
        self.stdout.write("  manager / Password123!")
        self.stdout.write("  tech1 / Password123!")
        self.stdout.write("  req1 / Password123!")
        self.stdout.write("AI author: ai_bot (no usable password)")

    def upsert_user(
        self,
        username,
        email,
        role,
        password,
        is_staff=False,
        is_superuser=False,
    ):
        user, _ = User.objects.update_or_create(
            username=username,
            defaults={
                "email": email,
                "role": role,
                "is_active": True,
                "is_staff": is_staff,
                "is_superuser": is_superuser,
            },
        )
        user.set_password(password)
        user.save()
        return user

    def create_ai_bot(self):
        bot, _ = User.objects.update_or_create(
            username="ai_bot",
            defaults={
                "email": "",
                "role": "ADMIN",
                "is_active": True,
                "is_staff": False,
                "is_superuser": False,
            },
        )
        bot.set_unusable_password()
        bot.save()

    def seed_sla_rules(self):
        sla_rules = [
            ("CRITICAL", 15, 120),
            ("HIGH", 30, 240),
            ("MEDIUM", 120, 480),
            ("LOW", 240, 1440),
        ]

        for priority, response_minutes, resolve_minutes in sla_rules:
            SLAConfig.objects.update_or_create(
                priority=priority,
                defaults={
                    "response_minutes": response_minutes,
                    "resolve_minutes": resolve_minutes,
                },
            )

    def seed_knowledge_base(self, technician):
        articles = [
            {
                "title": "Blue Screen (BSOD) Troubleshooting",
                "body": """Overview
A Windows blue screen (BSOD) means the computer encountered a serious error. Common causes include driver problems, hardware issues, or damaged system files.

First steps
1. Take a photo of the screen and note the STOP code or any file name shown.
2. Write down what happened just before the error (for example, a software update or new device).
3. If safe, disconnect recently connected USB devices and restart the computer once.

Troubleshooting
1. Install available Windows updates and restart.
2. If the problem began after a driver update, ask IT to check or roll back that driver.
3. If Windows starts in Safe Mode, note that for IT and avoid uninstalling company software.
4. Do not run administrator commands or open the computer case unless IT instructs you to.

Information to include in an IT ticket
- Photo or STOP code from the blue screen
- Approximate time and frequency of the crashes
- Recent updates or hardware changes
- Whether the computer can start normally

Contact IT urgently if the computer repeatedly crashes or cannot start.""",
                "is_public": True,
                "is_archived": False,
                "created_by": technician,
            },
            {
                "title": "WiFi Slow Troubleshooting",
                "body": """Goal
Use these checks to determine whether slow WiFi affects one device or the whole area.

Quick checks
1. Check the WiFi signal and move closer to the access point if possible.
2. Turn WiFi off and on, then reconnect to the approved company network.
3. Try another approved website or service.
4. Check whether another device nearby has the same problem.

Windows checks
1. Disconnect from WiFi and reconnect.
2. Restart the computer if convenient.
3. If your IT team permits it, open Command Prompt and run:
   ipconfig /flushdns

Do not restart or change company routers, access points, or network settings unless IT authorizes it.

Include in an IT ticket
- Your office location
- The WiFi network name (SSID), if appropriate
- When the issue started
- Whether other devices are affected
- A speed-test result or screenshot, if company policy permits

Contact IT if multiple users are affected or the connection remains slow.""",
                "is_public": True,
                "is_archived": False,
                "created_by": technician,
            },
            {
                "title": "Reset Password Steps",
                "body": """Self-service password reset
1. Open your organization's official password-reset page.
2. Enter your company username or work email address.
3. Complete the identity verification requested by your organization.
4. Create a new password that follows your organization's password policy.
5. Sign in again using the new password.

If you cannot reset your password
1. Check that Caps Lock is off and the keyboard layout is correct.
2. Confirm that you are using your company username, not a display name.
3. If your account is locked, follow your organization's instructions or contact IT.

Security reminders
- Never share your password, one-time code, or MFA approval with anyone.
- IT staff should not ask you to disclose your current password.
- Use only the official company password-reset page.

When contacting IT, provide your username and the error message you see. Do not include your password or verification code.""",
                "is_public": True,
                "is_archived": False,
                "created_by": technician,
            },
        ]

        for article_data in articles:
            title = article_data["title"]
            defaults = {
                key: value for key, value in article_data.items() if key != "title"
            }

            KBArticle.objects.update_or_create(
                title=title,
                defaults=defaults,
            )

        self.stdout.write(self.style.SUCCESS("Created/updated 3 KB articles."))

    def seed_tickets(self, requester, technician):
        demo_tickets = [
            {
                "title": "Cannot login - password forgotten",
                "description": "I forgot my password and cannot log in.",
                "category": Ticket.Category.ACCOUNT,
                "priority": Ticket.Priority.HIGH,
            },
            {
                "title": "Internet is very slow",
                "description": "WiFi has been slow since this morning.",
                "category": Ticket.Category.NETWORK,
                "priority": Ticket.Priority.CRITICAL,
            },
        ]

        for ticket_data in demo_tickets:
            title = ticket_data["title"]
            defaults = {
                **ticket_data,
                "assigned_to": technician,
                "status": Ticket.Status.OPEN,
                "is_archived": False,
            }

            Ticket.objects.update_or_create(
                title=title,
                requester=requester,
                defaults=defaults,
            )
