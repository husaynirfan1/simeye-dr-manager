"""
Views for schedule management.
"""
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from datetime import date, timedelta
from django.utils import timezone

from .models import ScheduleSession
from .api_client import (
    fetch_schedule_from_api,
    sync_schedule_to_db,
    generate_time_slots,
    ScheduleAPIError
)


@login_required
def schedule_view(request):
    """View schedule for journey log creation"""
    if not request.user.can_view_schedule():
        messages.error(request, 'You do not have permission to view the schedule.')
        return redirect('deficiencies:dashboard')

    conn_open = True  # Track if API is accessible

    try:
        # Get date range (next 7 days)
        today = date.today()
        dates = [(today + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]

        # Get time slots
        time_slots = generate_time_slots()

        # Fetch existing sessions from database
        existing_sessions = {}
        for row in ScheduleSession.objects.filter(
            session_date__in=dates,
            resource='AW139'
        ):
            key = f"{row.session_date}_{row.time_slot}"
            existing_sessions[key] = {
                'is_booked': row.is_booked,
                'is_completed': row.is_completed,
                'journey_log_id': row.journey_log_id,
                'customer': row.customer,
                'end_time': row.end_time
            }

        # Try to fetch from external API and sync to database
        if dates:
            api_sessions = fetch_schedule_from_api(dates[0], dates[-1])

            for session in api_sessions:
                key = f"{session.get('date')}_{session.get('time_slot')}"

                # Check if session exists in database
                if key not in existing_sessions:
                    # Insert new session from API
                    ScheduleSession.objects.create(
                        session_date=session.get('date'),
                        time_slot=session.get('time_slot'),
                        end_time=session.get('end_time'),
                        resource='AW139',
                        customer=session.get('customer', ''),
                        is_booked=bool(session.get('customer'))
                    )

                    existing_sessions[key] = {
                        'is_booked': True,
                        'is_completed': False,
                        'journey_log_id': None,
                        'customer': session.get('customer', ''),
                        'end_time': session.get('end_time', '')
                    }
                else:
                    # Update existing session with API data
                    if session.get('customer') and session.get('customer') != existing_sessions[key].get('customer'):
                        ScheduleSession.objects.filter(
                            session_date=session.get('date'),
                            time_slot=session.get('time_slot'),
                            resource='AW139'
                        ).update(
                            customer=session.get('customer'),
                            end_time=session.get('end_time')
                        )
                        existing_sessions[key]['customer'] = session.get('customer')
                        existing_sessions[key]['end_time'] = session.get('end_time')

        context = {
            'dates': dates,
            'time_slots': time_slots,
            'sessions': existing_sessions,
            'api_available': True,
        }
        return render(request, 'schedule/index.html', context)

    except ScheduleAPIError as e:
        # API unavailable - show 503 page
        conn_open = False
        return render(request, 'errors/503.html', {
            'error_message': str(e)
        }, status=503)


@login_required
def book_slot(request):
    """Book a schedule slot and redirect to journey log creation"""
    if not request.user.can_view_schedule():
        messages.error(request, 'You do not have permission to book schedule slots.')
        return redirect('schedule:view')

    session_date = request.POST.get('session_date')
    time_slot = request.POST.get('time_slot')

    if not session_date or not time_slot:
        messages.error(request, 'Invalid schedule slot')
        return redirect('schedule:view')

    try:
        # Check if slot exists and is available
        slot, created = ScheduleSession.objects.get_or_create(
            session_date=session_date,
            time_slot=time_slot,
            resource='AW139',
            defaults={'is_booked': True}
        )

        if slot.is_completed:
            messages.error(request, 'This session has already been completed')
            return redirect('schedule:view')

        # Mark as booked
        if not created:
            slot.is_booked = True
            slot.save()

        # Redirect to journey log creation with pre-filled data
        from django.urls import reverse
        return redirect(reverse('journey_logs:create') + f'?slot_id={slot.id}&session_date={session_date}&time_slot={time_slot}&customer_name={slot.customer or ""}')

    except Exception as e:
        messages.error(request, f'Error booking slot: {e}')
        return redirect('schedule:view')


@login_required
def refresh_schedule(request):
    """API endpoint to refresh schedule data from external API"""
    if not request.user.can_view_schedule():
        return JsonResponse({'error': 'Permission denied'}, status=403)

    start_date = request.GET.get('start')
    end_date = request.GET.get('end')

    if not start_date or not end_date:
        return JsonResponse({'error': 'Missing date range'}, status=400)

    try:
        success, message, count = sync_schedule_to_db(start_date, end_date)

        if success:
            return JsonResponse({
                'success': True,
                'message': message,
                'sessions': count
            })
        else:
            return JsonResponse({
                'success': False,
                'error': message
            }, status=503)

    except ScheduleAPIError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=503)
