"""
Views for journey log management.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.utils import timezone

from .models import JourneyLog, JourneyLogCrew, JourneyLogDR
from apps.deficiencies.models import Deficiency


@login_required
def journey_log_list(request):
    """List all journey logs"""
    journey_logs = JourneyLog.objects.annotate(
        linked_dr_count=Count('dr_links')
    ).all()

    context = {
        'journey_logs': journey_logs,
    }
    return render(request, 'journey_logs/list.html', context)


@login_required
def journey_log_detail(request, pk):
    """View single journey log with linked DRs"""
    journey_log = get_object_or_404(JourneyLog, pk=pk)

    # Get crew members
    crew = journey_log.crew_members

    # Get linked DRs
    linked_drs = journey_log.linked_deficiencies.select_related('deficiency')

    # Get all DRs for potential linking
    all_drs = Deficiency.objects.order_by('-deficiency_number')[:100]

    context = {
        'journey_log': journey_log,
        'crew': crew,
        'linked_drs': linked_drs,
        'all_drs': all_drs,
    }
    return render(request, 'journey_logs/detail.html', context)


@login_required
def journey_log_create(request):
    """Create new journey log"""
    if not request.user.can_edit_journey_logs():
        messages.error(request, 'You do not have permission to create journey logs.')
        return redirect('journey_logs:list')

    if request.method == 'POST':
        # Get form data
        customer_name = request.POST.get('customer_name', '')
        log_date = request.POST.get('log_date')
        site = request.POST.get('site', '')
        resource_type = request.POST.get('resource_type', '')
        resource = request.POST.get('resource', '')
        session_type = request.POST.get('session_type', '')
        training_type = request.POST.get('training_type', '')
        report_by = request.POST.get('report_by', '')
        schedule_slot_id = request.POST.get('schedule_slot_id')

        # Create journey log
        journey_log = JourneyLog.objects.create(
            customer_name=customer_name,
            log_date=log_date,
            site=site,
            resource_type=resource_type,
            resource=resource,
            session_type=session_type,
            training_type=training_type,
            report_by=report_by,
            schedule_slot_id=int(schedule_slot_id) if schedule_slot_id else None
        )

        # Link journey log to schedule slot if provided
        if schedule_slot_id:
            from apps.schedule.models import ScheduleSession
            try:
                schedule_slot = ScheduleSession.objects.get(id=schedule_slot_id)
                schedule_slot.journey_log = journey_log
                schedule_slot.save()
            except ScheduleSession.DoesNotExist:
                pass

        # Insert crew members
        crew_names = request.POST.getlist('crew_name[]')
        license_numbers = request.POST.getlist('license_number[]')
        crew_types = request.POST.getlist('crew_type[]')

        for i, name in enumerate(crew_names):
            if name.strip():
                license_num = license_numbers[i] if i < len(license_numbers) else ''
                crew_type = crew_types[i] if i < len(crew_types) else ''

                JourneyLogCrew.objects.create(
                    journey_log=journey_log,
                    crew_name=name,
                    license_number=license_num,
                    crew_type=crew_type
                )

        # Link DRs if provided
        linked_drs = request.POST.getlist('linked_dr_numbers[]')
        for dr_num in linked_drs:
            if dr_num.strip().isdigit():
                JourneyLogDR.objects.create(
                    journey_log=journey_log,
                    deficiency_number=int(dr_num)
                )

        messages.success(request, 'Journey Log created successfully!')
        return redirect('journey_logs:detail', pk=journey_log.id)

    # GET request - show form
    # Get unique values from deficiencies for dropdowns
    sites = Deficiency.objects.values_list('site_name', flat=True).filter(
        site_name__isnull=False
    ).distinct().order_by('site_name')
    resources = Deficiency.objects.values_list('resource', flat=True).filter(
        resource__isnull=False
    ).distinct().order_by('resource')

    context = {
        'sites': sites,
        'resources': resources,
    }
    return render(request, 'journey_logs/form.html', context)


@login_required
def journey_log_update(request, pk):
    """Edit existing journey log"""
    if not request.user.can_edit_journey_logs():
        messages.error(request, 'You do not have permission to edit journey logs.')
        return redirect('journey_logs:detail', pk=pk)

    journey_log = get_object_or_404(JourneyLog, pk=pk)

    if request.method == 'POST':
        # Update fields
        journey_log.customer_name = request.POST.get('customer_name', '')
        journey_log.log_date = request.POST.get('log_date')
        journey_log.site = request.POST.get('site', '')
        journey_log.resource_type = request.POST.get('resource_type', '')
        journey_log.resource = request.POST.get('resource', '')
        journey_log.session_type = request.POST.get('session_type', '')
        journey_log.training_type = request.POST.get('training_type', '')
        journey_log.report_by = request.POST.get('report_by', '')
        journey_log.save()

        messages.success(request, 'Journey Log updated successfully!')
        return redirect('journey_logs:detail', pk=pk)

    context = {
        'journey_log': journey_log,
    }
    return render(request, 'journey_logs/form.html', context)


@login_required
def journey_log_delete(request, pk):
    """Delete journey log"""
    if not request.user.has_full_access():
        messages.error(request, 'Only administrators can delete journey logs.')
        return redirect('journey_logs:detail', pk=pk)

    journey_log = get_object_or_404(JourneyLog, pk=pk)

    if request.method == 'POST':
        journey_log.delete()
        messages.success(request, 'Journey Log deleted successfully!')
        return redirect('journey_logs:list')

    context = {'journey_log': journey_log}
    return render(request, 'journey_logs/confirm_delete.html', context)


@login_required
def journey_log_generate(request, pk):
    """Generate journey log for printing"""
    journey_log = get_object_or_404(JourneyLog, pk=pk)

    # Mark schedule slot as completed if linked
    if journey_log.schedule_slot_id:
        from apps.schedule.models import ScheduleSession
        try:
            schedule_slot = ScheduleSession.objects.get(id=journey_log.schedule_slot_id)
            schedule_slot.is_completed = True
            schedule_slot.save()
        except ScheduleSession.DoesNotExist:
            pass

    crew = journey_log.crew_members
    linked_drs = journey_log.linked_deficiencies.select_related('deficiency')

    context = {
        'journey_log': journey_log,
        'crew': crew,
        'linked_drs': linked_drs,
    }
    return render(request, 'journey_logs/generate.html', context)


@login_required
def link_dr(request, journey_log_id):
    """Link DRs to a journey log"""
    if not request.user.can_edit_journey_logs():
        messages.error(request, 'You do not have permission to link DRs.')
        return redirect('journey_logs:detail', pk=journey_log_id)

    journey_log = get_object_or_404(JourneyLog, pk=journey_log_id)

    if request.method == 'POST':
        dr_numbers = request.POST.getlist('dr_numbers[]')

        for dr_num in dr_numbers:
            if dr_num.strip().isdigit():
                # Check if already linked
                if not JourneyLogDR.objects.filter(
                    journey_log=journey_log,
                    deficiency_number=int(dr_num)
                ).exists():
                    JourneyLogDR.objects.create(
                        journey_log=journey_log,
                        deficiency_number=int(dr_num)
                    )

        messages.success(request, 'Deficiencies linked successfully!')

    return redirect('journey_logs:detail', pk=journey_log_id)


@login_required
def unlink_dr(request, journey_log_id, deficiency_number):
    """Unlink a DR from a journey log"""
    if not request.user.can_edit_journey_logs():
        messages.error(request, 'You do not have permission to unlink DRs.')
        return redirect('journey_logs:detail', pk=journey_log_id)

    link = get_object_or_404(
        JourneyLogDR,
        journey_log_id=journey_log_id,
        deficiency_number=deficiency_number
    )

    if request.method == 'POST':
        link.delete()
        messages.success(request, 'Deficiency unlinked successfully!')

    return redirect('journey_logs:detail', pk=journey_log_id)
