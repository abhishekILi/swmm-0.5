from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from master.models import Department, Ship
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

from users.models import GalleryImage, User, UserMessage


def get_test_image():
    file = BytesIO()
    image = Image.new("RGB", (100, 100))
    image.save(file, "JPEG")
    file.seek(0)

    return SimpleUploadedFile(
        "test.jpg",
        file.read(),
        content_type="image/jpeg",
    )


class UserAppTests(APITestCase):
    def setUp(self):
        self.department = Department.objects.create(name="Engineering")

        self.ship = Ship.objects.create(name="INS Vikrant")

        self.user = User.objects.create_user(
            username="testuser",
            password="Password123",
            first_name="John",
            last_name="Doe",
            personnel_number="12345",
            department=self.department,
            ship=self.ship,
        )

    # ======================================================
    # User Model Tests
    # ======================================================

    def test_user_str(self):
        self.assertEqual(str(self.user), "John Doe 12345")

    def test_create_user(self):
        user = User.objects.create_user(
            username="newuser",
            password="Password123",
            personnel_number="99999",
        )

        self.assertEqual(user.CustomUsername, "newuser")
        self.assertEqual(user.personnel_number, "99999")

    def test_user_manager_supports_auth_natural_key_lookup(self):
        looked_up = User.objects.get_by_natural_key("testuser")

        self.assertEqual(looked_up.pk, self.user.pk)

    # ======================================================
    # User ViewSet Tests
    # ======================================================

    # def test_user_list(self): #NOSONAR
    #     url = reverse("user-list")

    #     response = self.client.get(url)#NOSONAR

    #     self.assertEqual(response.status_code, status.HTTP_200_OK)

    # def test_user_retrieve(self):#NOSONAR
    #     url = reverse("user-detail", kwargs={"pk": self.user.id})

    #     response = self.client.get(url)#NOSONAR

    #     self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_user_create_api(self):
        url = reverse("register-user")

        payload = {
            "username": "createduser",
            "password": "Password123",
            "personnel_number": "88888",
        }

        response = self.client.post(
            url,
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertTrue(User.objects.filter(username="createduser").exists())

    # def test_user_delete(self):#NOSONAR
    #     url = reverse("user-detail", kwargs={"pk": self.user.id})

    #     response = self.client.delete(url)#NOSONAR

    #     self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    # ======================================================
    # Login Tests
    # ======================================================

    def test_login_success(self):
        url = reverse("token")
        response = self.client.post(
            url,
            {
                "username": "testuser",
                "password": "Password123",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_invalid_credentials(self):
        url = reverse("token")
        response = self.client.post(
            url,
            {
                "username": "wrong",
                "password": "wrong",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ======================================================
    # Gallery Model Tests
    # ======================================================

    def test_gallery_image_str(self):
        image = SimpleUploadedFile(
            "test.jpg", b"filecontent", content_type="image/jpeg"
        )

        gallery = GalleryImage.objects.create(
            image=image,
            title="Gallery Title",
            caption="Caption",
            ship=self.ship,
        )

        self.assertEqual(str(gallery), "Gallery Title")

    # ======================================================
    # Gallery API Tests
    # ======================================================

    def test_gallery_create(self):
        image = get_test_image()

        url = reverse("gallery-list")

        payload = {
            "title": "Gallery",
            "caption": "Caption",
            "ship": self.ship.id,
            "image": image,
        }

        response = self.client.post(
            url,
            payload,
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(response.data["status"], "success")

    def test_gallery_list(self):
        image = SimpleUploadedFile(
            "test.jpg", b"filecontent", content_type="image/jpeg"
        )

        GalleryImage.objects.create(
            image=image,
            title="Gallery",
            caption="Caption",
            ship=self.ship,
        )

        response = self.client.get(reverse("gallery-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(response.data), 1)

    def test_gallery_filter_by_ship(self):
        image = SimpleUploadedFile(
            "test.jpg", b"filecontent", content_type="image/jpeg"
        )

        GalleryImage.objects.create(
            image=image,
            title="Gallery",
            caption="Caption",
            ship=self.ship,
        )

        response = self.client.get(
            reverse("gallery-list"),
            {"ship_id": self.ship.id},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(response.data), 1)

    def test_gallery_delete(self):
        image = SimpleUploadedFile(
            "test.jpg", b"filecontent", content_type="image/jpeg"
        )

        gallery = GalleryImage.objects.create(
            image=image,
            title="Gallery",
            caption="Caption",
            ship=self.ship,
        )

        response = self.client.delete(
            reverse("gallery-detail", kwargs={"pk": gallery.id})
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertFalse(GalleryImage.objects.filter(id=gallery.id).exists())

    # ======================================================
    # UserMessage ViewSet Tests
    # ======================================================

    def test_user_messages_requires_authentication(self):
        url = reverse("user-messages-list")

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_message_list_returns_recipient_messages(self):
        other_user = User.objects.create_user(
            username="otheruser",
            password="Password123",
            personnel_number="54321",
            department=self.department,
            ship=self.ship,
        )

        UserMessage.objects.create(
            sender=other_user,
            recipient=self.user,
            msg_title="Incoming",
            msg_short_title="Incoming",
            msg_body="Hello",
            status="unread",
        )
        UserMessage.objects.create(
            sender=self.user,
            recipient=other_user,
            msg_title="Outgoing",
            msg_short_title="Outgoing",
            msg_body="Hi",
            status="unread",
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("user-messages-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["msg_title"], "Incoming")

    def test_user_message_inbox_endpoint(self):
        other_user = User.objects.create_user(
            username="sender",
            password="Password123",
            personnel_number="67890",
            department=self.department,
            ship=self.ship,
        )

        UserMessage.objects.create(
            sender=other_user,
            recipient=self.user,
            msg_title="Inbox Message",
            msg_short_title="Inbox",
            msg_body="Inbox body",
            status="unread",
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("user-messages-inbox"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["msg_title"], "Inbox Message")

    def test_user_message_outbox_endpoint(self):
        recipient = User.objects.create_user(
            username="recipient",
            password="Password123",
            personnel_number="11111",
            department=self.department,
            ship=self.ship,
        )

        UserMessage.objects.create(
            sender=self.user,
            recipient=recipient,
            msg_title="Outbox Message",
            msg_short_title="Outbox",
            msg_body="Outbox body",
            status="unread",
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("user-messages-outbox"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["msg_title"], "Outbox Message")

    def test_mark_read_updates_message_status_for_recipient(self):
        sender = User.objects.create_user(
            username="sender2",
            password="Password123",
            personnel_number="22222",
            department=self.department,
            ship=self.ship,
        )

        message = UserMessage.objects.create(
            sender=sender,
            recipient=self.user,
            msg_title="Mark Read",
            msg_short_title="Mark",
            msg_body="Please read",
            status="unread",
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            reverse("user-messages-mark-read", kwargs={"pk": message.id}),
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        message.refresh_from_db()
        self.assertEqual(message.status, "read")

    def test_mark_read_denied_for_non_recipient(self):
        recipient = User.objects.create_user(
            username="recipient2",
            password="Password123",
            personnel_number="33333",
            department=self.department,
            ship=self.ship,
        )

        message = UserMessage.objects.create(
            sender=self.user,
            recipient=recipient,
            msg_title="Not Yours",
            msg_short_title="Not",
            msg_body="No access",
            status="unread",
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            reverse("user-messages-mark-read", kwargs={"pk": message.id}),
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unread_count_returns_only_unread_messages(self):
        other_user = User.objects.create_user(
            username="sender3",
            password="Password123",
            personnel_number="44444",
            department=self.department,
            ship=self.ship,
        )

        UserMessage.objects.create(
            sender=other_user,
            recipient=self.user,
            msg_title="Unread One",
            msg_short_title="Unread",
            msg_body="Unread body",
            status="unread",
        )
        UserMessage.objects.create(
            sender=other_user,
            recipient=self.user,
            msg_title="Read One",
            msg_short_title="Read",
            msg_body="Read body",
            status="read",
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("user-messages-unread-count"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    # ======================================================
    # Birthday API Tests
    # ======================================================

    def test_ship_birthdays(self):
        User.objects.create(
            username="birthdayuser",
            personnel_number="22222",
            ship=self.ship,
            department=self.department,
            date_of_birth="1990-01-01",
            is_active=True,
        )

        response = self.client.get(
            reverse(
                "ship-birthdays",
                kwargs={"ship_id": self.ship.id},
            )
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(response.data), 1)

    def test_ship_birthdays_excludes_inactive(self):
        User.objects.create(
            username="inactive",
            personnel_number="33333",
            ship=self.ship,
            department=self.department,
            date_of_birth="1990-01-01",
            is_active=False,
        )

        response = self.client.get(
            reverse(
                "ship-birthdays",
                kwargs={"ship_id": self.ship.id},
            )
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(response.data), 0)

    def test_ship_birthdays_excludes_null_dob(self):
        User.objects.create(
            username="nodob",
            personnel_number="44444",
            ship=self.ship,
            department=self.department,
            is_active=True,
        )

        response = self.client.get(
            reverse(
                "ship-birthdays",
                kwargs={"ship_id": self.ship.id},
            )
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(response.data), 0)
