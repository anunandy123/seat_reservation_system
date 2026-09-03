import json

from django.db import models, transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .models import Event, Reservation, Seat


def _event():
    event, created = Event.objects.get_or_create(pk=1)
    if created:
        Seat.objects.bulk_create([
            Seat(event=event, label=f'{row}{number}', row=row, number=number)
            for row in range(1, 7) for number in range(1, 13)
        ])
    return event


def _release_expired(event):
    now = timezone.now()
    expired = Reservation.objects.filter(event=event, status=Reservation.HOLD, expires_at__lte=now)
    expired_ids = list(expired.values_list('id', flat=True))
    expired.update(status=Reservation.EXPIRED)
    Seat.objects.filter(event=event, state=Seat.HELD).filter(
        models.Q(hold_expires_at__lte=now) | models.Q(current_reservation_id__in=expired_ids)
    ).update(
        state=Seat.AVAILABLE, current_reservation=None, hold_expires_at=None
    )


def _session(request):
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


@require_GET
def seat_map(request):
    event = _event()
    return render(request, 'reservations/seat_map.html', {'event': event})


@require_GET
def availability(request):
    event = _event()
    with transaction.atomic():
        _release_expired(event)
        seats = list(event.seats.values('id', 'label', 'row', 'number', 'state'))
    return JsonResponse({'event': event.name, 'seats': seats})


@require_POST
def reserve(request):
    try:
        payload = json.loads(request.body)
        if not isinstance(payload, dict):
            raise ValueError
        seat_ids = {int(value) for value in payload.get('seat_ids', [])}
    except (ValueError, TypeError, json.JSONDecodeError, AttributeError):
        return JsonResponse({'error': 'Choose valid seats.'}, status=400)
    if not seat_ids:
        return JsonResponse({'error': 'Choose at least one seat.'}, status=400)

    event = _event()
    session_key = _session(request)
    with transaction.atomic():
        _release_expired(event)
        previous_holds = list(Reservation.objects.select_for_update().filter(
            session_key=session_key, event=event, status=Reservation.HOLD
        ))
        previous_ids = [hold.pk for hold in previous_holds]
        previous_seat_ids = set(Seat.objects.filter(current_reservation_id__in=previous_ids).values_list('id', flat=True))
        seats = list(Seat.objects.select_for_update().filter(
            event=event, id__in=seat_ids | previous_seat_ids
        ).order_by('id'))
        requested_seats = [seat for seat in seats if seat.id in seat_ids]
        if len(requested_seats) != len(seat_ids):
            return JsonResponse({'error': 'One or more seats do not exist.'}, status=400)
        if any(seat.state != Seat.AVAILABLE and seat.current_reservation_id not in previous_ids for seat in requested_seats):
            return JsonResponse({'error': 'One or more selected seats are no longer available.'}, status=409)
        if previous_ids:
            Seat.objects.filter(current_reservation_id__in=previous_ids).update(
                state=Seat.AVAILABLE, current_reservation=None, hold_expires_at=None
            )
            Reservation.objects.filter(pk__in=previous_ids).update(status=Reservation.EXPIRED)
        reservation = Reservation.new_hold(event, session_key)
        Seat.objects.filter(pk__in=seat_ids).update(
            state=Seat.HELD, current_reservation=reservation, hold_expires_at=reservation.expires_at
        )
    return JsonResponse({'token': str(reservation.token), 'expires_at': reservation.expires_at.isoformat()})


@require_POST
def checkout(request):
    token = request.headers.get('X-Reservation-Token')
    reservation = get_object_or_404(Reservation, token=token or '')
    with transaction.atomic():
        reservation = Reservation.objects.select_for_update().get(pk=reservation.pk)
        if reservation.status != Reservation.HOLD or reservation.expires_at <= timezone.now():
            reservation.status = Reservation.EXPIRED
            reservation.save(update_fields=['status'])
            Seat.objects.filter(current_reservation=reservation).update(
                state=Seat.AVAILABLE, current_reservation=None, hold_expires_at=None
            )
            return JsonResponse({'error': 'This hold has expired.'}, status=409)
        seats = Seat.objects.select_for_update().filter(current_reservation=reservation)
        seats.update(state=Seat.BOOKED, current_reservation=None, hold_expires_at=None)
        reservation.status = Reservation.BOOKED
        reservation.save(update_fields=['status'])
    return JsonResponse({'status': 'booked'})
