import uuid
from datetime import timedelta

from django.db import models
from django.utils import timezone


class Event(models.Model):
	name = models.CharField(max_length=160, default='Friday Night Live')
	venue = models.CharField(max_length=160, default='The Grand Hall')
	starts_at = models.DateTimeField(default=timezone.now)

	def __str__(self):
		return self.name


class Reservation(models.Model):
	HOLD_MINUTES = 2
	HOLD = 'hold'
	BOOKED = 'booked'
	EXPIRED = 'expired'
	STATUS_CHOICES = [(HOLD, 'Hold'), (BOOKED, 'Booked'), (EXPIRED, 'Expired')]

	token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
	event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='reservations')
	session_key = models.CharField(max_length=40)
	status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=HOLD)
	expires_at = models.DateTimeField()
	created_at = models.DateTimeField(auto_now_add=True)

	@classmethod
	def new_hold(cls, event, session_key):
		return cls.objects.create(
			event=event,
			session_key=session_key,
			expires_at=timezone.now() + timedelta(minutes=cls.HOLD_MINUTES),
		)


class Seat(models.Model):
	AVAILABLE = 'available'
	HELD = 'held'
	BOOKED = 'booked'
	STATE_CHOICES = [(AVAILABLE, 'Available'), (HELD, 'Held'), (BOOKED, 'Booked')]

	event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='seats')
	label = models.CharField(max_length=12)
	row = models.PositiveIntegerField()
	number = models.PositiveIntegerField()
	state = models.CharField(max_length=12, choices=STATE_CHOICES, default=AVAILABLE)
	current_reservation = models.ForeignKey(
		Reservation, null=True, blank=True, on_delete=models.SET_NULL, related_name='held_seats'
	)
	hold_expires_at = models.DateTimeField(null=True, blank=True)

	class Meta:
		ordering = ['row', 'number']
		constraints = [models.UniqueConstraint(fields=['event', 'label'], name='unique_event_seat')]

	def __str__(self):
		return self.label

# Create your models here.
