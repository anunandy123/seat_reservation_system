import json
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from .models import Event, Reservation, Seat


class ReservationFlowTests(TestCase):
	def setUp(self):
		self.client.get('/')
		self.event = Event.objects.get(pk=1)
		self.seat = self.event.seats.first()

	def hold(self, client, *seat_ids):
		return client.post('/api/reservation/', data=json.dumps({'seat_ids': seat_ids}), content_type='application/json')

	def test_first_request_wins_and_second_request_cannot_duplicate(self):
		first = self.hold(self.client, self.seat.id)
		second = self.hold(self.client_class(), self.seat.id)

		self.assertEqual(first.status_code, 200)
		self.assertEqual(second.status_code, 409)
		self.assertEqual(Seat.objects.get(pk=self.seat.id).state, Seat.HELD)

	def test_same_session_can_modify_selection(self):
		another = self.event.seats.all()[1]
		self.assertEqual(self.hold(self.client, self.seat.id).status_code, 200)
		response = self.hold(self.client, another.id)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(Seat.objects.get(pk=self.seat.id).state, Seat.AVAILABLE)
		self.assertEqual(Seat.objects.get(pk=another.id).state, Seat.HELD)

	def test_failed_modification_keeps_existing_hold(self):
		another_client = self.client_class()
		another_client.get('/')
		self.assertEqual(self.hold(another_client, self.seat.id).status_code, 200)
		self.assertEqual(self.hold(self.client, self.event.seats.all()[1].id).status_code, 200)

		response = self.hold(self.client, self.seat.id)

		self.assertEqual(response.status_code, 409)
		self.assertEqual(Seat.objects.get(pk=self.event.seats.all()[1].id).state, Seat.HELD)

	def test_expired_hold_is_released(self):
		response = self.hold(self.client, self.seat.id)
		reservation = Reservation.objects.get(token=response.json()['token'])
		reservation.expires_at = timezone.now() - timedelta(seconds=1)
		reservation.save(update_fields=['expires_at'])

		availability = self.client.get('/api/availability/')

		self.assertEqual(availability.status_code, 200)
		self.assertEqual(availability.json()['seats'][0]['state'], Seat.AVAILABLE)

	def test_checkout_converts_hold_to_booked(self):
		response = self.hold(self.client, self.seat.id)
		booked = self.client.post('/api/reservation/checkout/', HTTP_X_RESERVATION_TOKEN=response.json()['token'])

		self.assertEqual(booked.status_code, 200)
		self.assertEqual(Seat.objects.get(pk=self.seat.id).state, Seat.BOOKED)

# Create your tests here.
