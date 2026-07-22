"""
Views for deficiency management.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Count, Max
from django.utils import timezone
from datetime import datetime
from .utility import normalize_date
from apps.core.mixins import (
    AdminRequiredMixin, TechnicianRequiredMixin, ViewerRequiredMixin
)
from .models import Deficiency
from .forms import (
    DeficiencyForm, QuickFilterForm, ActionAddForm, DeficiencyBulkEditForm
)


# ============================================================================
# Dashboard View
# ============================================================================

from django.core.cache import cache

@login_required
def dashboard(request):
    """Dashboard with statistics and tabular data visualizations (Ultra-Fast Cached Version)"""
    from django.db.models import Count, Q
    from datetime import datetime
    
    # 1. Try to get the fully calculated dashboard from memory first
    context = cache.get('dashboard_metrics')

    # 2. If it's not in memory (or 5 minutes have passed), calculate it!
    if not context:
        all_deficiencies = Deficiency.objects.all()

        def calculate_type_stats(type_value):
            """Calculate statistics using a SINGLE database trip"""
            type_deficiencies = all_deficiencies.filter(deficiency_type__iexact=type_value)

            # DB FIX: Aggregate all counts at once instead of doing 6 separate queries
            stats = type_deficiencies.aggregate(
                total=Count('deficiency_number'),
                open=Count('deficiency_number', filter=Q(status='OPEN')),
                in_work=Count('deficiency_number', filter=Q(status='In Work')),
                monitoring=Count('deficiency_number', filter=Q(status='Monitoring')),
                on_offer=Count('deficiency_number', filter=Q(status='On Offer')),
                on_hold=Count('deficiency_number', filter=Q(status='On Hold')),
            )
            stats['type_name'] = type_value

            # Calculate duration breakdown for Training and Maintenance types
            if type_value.lower() in ('training', 'maintenance'):
                from dateutil.relativedelta import relativedelta

                today = datetime.now().date()
                # EDATE(TODAY(), -n) equivalents (calendar-month arithmetic, matching Excel's EDATE)
                edate_1 = today - relativedelta(months=1)
                edate_3 = today - relativedelta(months=3)
                edate_12 = today - relativedelta(months=12)

                less_1m, one_to_three_m, three_to_one_y, greater_1y = 0, 0, 0, 0

                # Memory Fix: Only fetch the date column, don't load the entire rows into memory!
                # Excludes 'Cleared' status to match the COUNTIFS logic ('ALL DR'!$H<>"Cleared")
                dates = (
                    type_deficiencies
                    .exclude(raised_date__isnull=True)
                    .exclude(status__iexact='Cleared')
                    .values_list('raised_date', flat=True)
                )

                for raised_date in dates:
                    try:
                        # Handle both date objects and string dates safely
                        if isinstance(raised_date, str):
                            raised_dt = datetime.strptime(raised_date, '%Y-%m-%d').date()
                        elif isinstance(raised_date, datetime):
                            raised_dt = raised_date.date()
                        else:
                            raised_dt = raised_date

                        # Mirrors the Excel COUNTIFS bucketing:
                        # <1m:      raised_date >= EDATE(TODAY(),-1)
                        # 1m<3m:    EDATE(TODAY(),-3) <= raised_date < EDATE(TODAY(),-1)
                        # 3m<1y:    EDATE(TODAY(),-12) <= raised_date < EDATE(TODAY(),-3)
                        # >1y:      raised_date < EDATE(TODAY(),-12)
                        if raised_dt >= edate_1:
                            less_1m += 1
                        elif raised_dt >= edate_3:
                            one_to_three_m += 1
                        elif raised_dt >= edate_12:
                            three_to_one_y += 1
                        else:
                            greater_1y += 1
                    except (ValueError, TypeError):
                        pass

                stats['duration_breakdown'] = {
                    'less_1m': less_1m, 'one_to_three_m': one_to_three_m,
                    'three_to_one_y': three_to_one_y, 'greater_1y': greater_1y,
                }
            return stats

        # Calculate stats for each type
        training_stats = calculate_type_stats('Training')
        maintenance_stats = calculate_type_stats('Maintenance')
        visual_modeling_stats = calculate_type_stats('Visual Modelling')

        total_active_dr = all_deficiencies.exclude(status__in=['Cleared', 'CLOSED']).count()

        status_counts = all_deficiencies.values('status').annotate(count=Count('deficiency_number')).order_by('-count')
        severity_counts = all_deficiencies.values('severity').annotate(count=Count('deficiency_number')).order_by('-count')
        
        # Build the final dictionary (we force lists so they cache properly)
        context = {
            'training_stats': training_stats,
            'maintenance_stats': maintenance_stats,
            'visual_modeling_stats': visual_modeling_stats,
            'total_active_dr': total_active_dr,
            'grand_total': all_deficiencies.count(), # <-- Add this line for the table!
            'recent_deficiencies': list(all_deficiencies[:10]),
            'status_counts': list(status_counts),
            'severity_counts': list(severity_counts),
        }
        
        # 3. Save to server memory for 1 minute (60 seconds)
        cache.set('dashboard_metrics', context, 20)

    return render(request, 'deficiencies/dashboard.html', context)

# ============================================================================
# List View
# ============================================================================

@login_required
def deficiency_list(request):
    """List all deficiencies with filtering and pagination"""
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    severity_filter = request.GET.get('severity', '')
    site_filter = request.GET.get('site', '')
    resource_filter = request.GET.get('resource', '')
    search = request.GET.get('search', '')

    # Build queryset
    deficiencies = Deficiency.objects.all()

    # Apply filters
    if status_filter:
        deficiencies = deficiencies.filter(status=status_filter)
    if severity_filter:
        deficiencies = deficiencies.filter(severity=severity_filter)
    if site_filter:
        deficiencies = deficiencies.filter(site_name=site_filter)
    if resource_filter:
        deficiencies = deficiencies.filter(resource=resource_filter)
    if search:
        deficiencies = deficiencies.filter(
            Q(deficiency_number__icontains=search) |
            Q(site_name__icontains=search) |
            Q(resource__icontains=search) |
            Q(issue_description__icontains=search) |
            Q(raised_by_name__icontains=search)
        )

    # Order by deficiency number descending
    deficiencies = deficiencies.order_by('-deficiency_number')

    # Pagination
    paginator = Paginator(deficiencies, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Get unique values for filters
    statuses = Deficiency.objects.values_list('status', flat=True).distinct().order_by('status')
    severities = Deficiency.objects.values_list('severity', flat=True).distinct().order_by('severity')
    sites = Deficiency.objects.values_list('site_name', flat=True).distinct().order_by('site_name')
    resources = Deficiency.objects.values_list('resource', flat=True).distinct().order_by('resource')

    context = {
        'deficiencies': page_obj,
        'page_obj': page_obj,
        'page': page_obj.number,              # <-- Add this line
        'page_range': paginator.get_elided_page_range(page_obj.number, on_each_side=2, on_ends=1),        'total_count': paginator.count,
        'total_pages': paginator.num_pages,
        'statuses': statuses,
        'severities': severities,
        'sites': sites,
        'resources': resources,
        'status_filter': status_filter,
        'severity_filter': severity_filter,
        'site_filter': site_filter,
        'resource_filter': resource_filter,
        'search': search,
    }
    return render(request, 'deficiencies/list.html', context)


# ============================================================================
# Detail View
# ============================================================================

@login_required
def deficiency_detail(request, deficiency_number):
    """View single deficiency details"""
    deficiency = get_object_or_404(Deficiency, deficiency_number=deficiency_number)

    # Parse actiontaken text for display
    actions = deficiency.parsed_actions

    context = {
        'deficiency': deficiency,
        'actions': actions,
        'action_form': ActionAddForm(user=request.user),
    }
    return render(request, 'deficiencies/detail.html', context)


# ============================================================================
# Create View
# ============================================================================

@login_required
def deficiency_create(request):
    """Create new deficiency"""
    if not request.user.can_edit_deficiency():
        messages.error(request, 'You do not have permission to create deficiencies.')
        return redirect('deficiencies:list')

    # Get next DR number
    next_num = Deficiency.objects.aggregate(
        next_num=Max('deficiency_number')
    )['next_num'] + 1 if Deficiency.objects.exists() else 1

    if request.method == 'POST':
        form = DeficiencyForm(request.POST, user=request.user)
        if form.is_valid():
            deficiency = form.save(commit=False)

            # Set DR number
            dr_number = request.POST.get('dr_number')
            if dr_number:
                try:
                    dr_number = int(dr_number)
                except ValueError:
                    dr_number = next_num
            else:
                dr_number = next_num

            # Verify DR number is still available
            if Deficiency.objects.filter(deficiency_number=dr_number).exists():
                # Number taken, get next available
                dr_number = next_num

            deficiency.deficiency_number = dr_number

           # Generate the dates
            now = timezone.now()
            today_date_obj = now.date()  # This is a proper Python date object
            
            # Legacy string formats for your display fields
            legacy_str_date = now.strftime('%d-%b-%Y').upper() 
            fld_date = now.strftime('%m/%d/%Y')                 

            # 1. Update the fields
            # Assign the proper date object to the DateFields
            deficiency.raised_date = today_date_obj
            deficiency.entered_date = today_date_obj
            deficiency.fld_raised_date = today_date_obj   # was fld_date (wrong format)
            deficiency.fld_due_date = today_date_obj      # was fld_date (wrong format)
            
            # 2. Update the hidden timestamp fields
            deficiency._raised_date = now
            deficiency._entered_date = now
            deficiency._due_date = now

            # If they are not an admin (or if the field is somehow blank), force their name securely
            if not request.user.has_full_access() or not deficiency.raised_by_name:
                deficiency.raised_by_name = request.user.get_full_name() or request.user.username

            # Always track who actually clicked the button
            deficiency.entered_by_name = request.user.get_full_name() or request.user.username

            # Ensure due_date has a value (DB has NOT NULL constraint)
            if not deficiency.due_date:
                from datetime import timedelta
                deficiency.due_date = (timezone.now().date() + timedelta(days=30))

       
            deficiency.save()

            # Clear dashboard cache so stats update immediately
            cache.delete('dashboard_metrics')

            messages.success(request, f'Deficiency #{dr_number} created successfully!')
            return redirect('deficiencies:detail', deficiency_number=dr_number)
    else:
        form = DeficiencyForm(user=request.user)

    # Get lookup values
    categories = Deficiency.objects.values_list('category_name', flat=True).distinct().order_by('category_name')
    systems = Deficiency.objects.values_list('system', flat=True).filter(
        system__isnull=False
    ).distinct().order_by('system')
    subsystems = Deficiency.objects.values_list('sub_system', flat=True).filter(
        sub_system__isnull=False
    ).distinct().order_by('sub_system')
    types = Deficiency.objects.values_list('type', flat=True).distinct().order_by('type')
    customers = Deficiency.objects.values_list('customer', flat=True).distinct().order_by('customer')
    resources = Deficiency.objects.values_list('resource', flat=True).distinct().order_by('resource')
    raised_by_names = Deficiency.objects.values_list('raised_by_name', flat=True).distinct().order_by('raised_by_name')
    deficiency_types = Deficiency.objects.exclude(deficiency_type__exact='').exclude(deficiency_type__isnull=True).values_list('deficiency_type', flat=True).distinct().order_by('deficiency_type')
    site_names = Deficiency.objects.values_list('site_name', flat=True).distinct().order_by('site_name')
    context = {
        'form': form,
        'categories': categories,
        'systems': systems,
        'subsystems': subsystems,
        'types': types,
        'customers': customers,
        'deficiency_types': deficiency_types,
        'next_dr_number': next_num,
        'site_names': site_names,
        'resources': resources,
        'raised_by_names': raised_by_names,
    }
    return render(request, 'deficiencies/form.html', context)


# ============================================================================
# Update View
# ============================================================================

@login_required
def deficiency_update(request, deficiency_number):
    """Edit existing deficiency"""
    if not request.user.can_edit_deficiency():
        messages.error(request, 'You do not have permission to edit deficiencies.')
        return redirect('deficiencies:detail', deficiency_number=deficiency_number)

    deficiency = get_object_or_404(Deficiency, deficiency_number=deficiency_number)

    if request.method == 'POST':
        form = DeficiencyForm(request.POST, instance=deficiency, user=request.user)
        if form.is_valid():
            deficiency = form.save(commit=False)

            # Normalize any string dates before saving (handles legacy formats from DB)
            date_fields = ['due_date', 'naa_due_date', 'on_offer_date', 'raised_date', 'entered_date', 'cleared_date']
            for field in date_fields:
                val = getattr(deficiency, field, None)
                if isinstance(val, str):
                    normalized = normalize_date(val)
                    if normalized:
                        setattr(deficiency, field, normalized)

            # Add ClearedDate timestamp if status changed to Cleared
            if deficiency.status == 'Cleared' and not deficiency.cleared_date:
                now = timezone.now()
                deficiency.cleared_date = now.date()
                deficiency._cleared_date = now

            # Ensure due_date has a value (DB has NOT NULL constraint)
            if not deficiency.due_date:
                from datetime import timedelta
                deficiency.due_date = (timezone.now().date() + timedelta(days=30))

            deficiency.save()

            # Clear dashboard cache so stats update immediately
            cache.delete('dashboard_metrics')

            messages.success(request, f'Deficiency #{deficiency_number} updated successfully!')
            return redirect('deficiencies:detail', deficiency_number=deficiency_number)
    else:
        form = DeficiencyForm(instance=deficiency, user=request.user)

    # Get lookup values (Safely excluding any blank/NULL junk from the legacy DB)
    categories = Deficiency.objects.exclude(category_name__isnull=True).exclude(category_name__exact='').values_list('category_name', flat=True).distinct().order_by('category_name')
    site_names = Deficiency.objects.exclude(site_name__isnull=True).exclude(site_name__exact='').values_list('site_name', flat=True).distinct().order_by('site_name')
    resources = Deficiency.objects.exclude(resource__isnull=True).exclude(resource__exact='').values_list('resource', flat=True).distinct().order_by('resource')
    deficiency_types = Deficiency.objects.exclude(deficiency_type__isnull=True).exclude(deficiency_type__exact='').values_list('deficiency_type', flat=True).distinct().order_by('deficiency_type')
    customers = Deficiency.objects.exclude(customer__isnull=True).exclude(customer__exact='').values_list('customer', flat=True).distinct().order_by('customer')
    
    systems = Deficiency.objects.exclude(system__isnull=True).exclude(system__exact='').values_list('system', flat=True).distinct().order_by('system')
    subsystems = Deficiency.objects.exclude(sub_system__isnull=True).exclude(sub_system__exact='').values_list('sub_system', flat=True).distinct().order_by('sub_system')
    types = Deficiency.objects.exclude(type__isnull=True).exclude(type__exact='').values_list('type', flat=True).distinct().order_by('type')

    context = {
        'form': form,
        'deficiency': deficiency,
        'categories': categories,
        'systems': systems,
        'subsystems': subsystems,
        'types': types,
        'site_names': site_names,
        'resources': resources,
        'deficiency_types': deficiency_types,
        'customers': customers,
    }
    return render(request, 'deficiencies/form.html', context)


# ============================================================================
# Delete View
# ============================================================================

@login_required
def deficiency_delete(request, deficiency_number):
    """Delete deficiency"""
    if not request.user.has_full_access():
        messages.error(request, 'Only administrators can delete deficiencies.')
        return redirect('deficiencies:detail', deficiency_number=deficiency_number)

    deficiency = get_object_or_404(Deficiency, deficiency_number=deficiency_number)

    if request.method == 'POST':
        deficiency.delete()

        # Clear dashboard cache so stats update immediately
        cache.delete('dashboard_metrics')

        messages.success(request, f'Deficiency #{deficiency_number} deleted successfully!')
        return redirect('deficiencies:list')

    context = {'deficiency': deficiency}
    return render(request, 'deficiencies/confirm_delete.html', context)


# ============================================================================
# Action Views
# ============================================================================

@login_required
def action_add(request, deficiency_number):
    """Add action to deficiency (appends to actiontaken text field)"""
    if not request.user.can_edit_deficiency():
        messages.error(request, 'You do not have permission to add actions.')
        return redirect('deficiencies:detail', deficiency_number=deficiency_number)

    deficiency = get_object_or_404(Deficiency, deficiency_number=deficiency_number)

    if request.method == 'POST':
        form = ActionAddForm(request.POST, user=request.user)
        if form.is_valid():
            # If they are a regular tech (or the field is blank), force their real name securely
            if not request.user.has_full_access() or not form.cleaned_data.get('username'):
                action_username = request.user.get_full_name() or request.user.username
            else:
                # If they are an admin, trust the name they selected from the dropdown
                action_username = form.cleaned_data.get('username')

            action_text = form.cleaned_data.get('action_text')

            # CRITICAL FIX: Clean the text so we don't break the regex parser in models.py!
            # Replace internal newlines with a spacer, and swap brackets for parentheses
            action_text = action_text.replace('\r\n', '<br>').replace('\n', '<br>')
            action_username = action_username.replace('[', '(').replace(']', ')')

            # 3. Format the new action string
            now = datetime.now()
            timestamp = now.strftime("%b %d %Y %I:%M%p")

            # Remove leading zero from hour for consistency with existing data
            import re
            timestamp = re.sub(r' 0(\d):', r'  \1:', timestamp)
            timestamp = re.sub(r'^0(\d):', r'\1:', timestamp)

            new_entry = f"[{timestamp}] [{action_username}] [{action_text}]"

            # 4. Append to existing actiontaken
            existing_actions = deficiency.actiontaken or ''
            if existing_actions:
                # Guarantee a clean line break separates the old actions from the new one
                if not existing_actions.endswith(('\n', '&#x0D;')):
                    new_entry = existing_actions + '\r\n' + new_entry
                else:
                    new_entry = existing_actions + new_entry

            # Update deficiency
            deficiency.actiontaken = new_entry
            deficiency.fld_last_action_taken_date = datetime.now().date()

            deficiency.save(update_fields=['actiontaken', 'fld_last_action_taken_date'])

            messages.success(request, 'Action added successfully!')
            return redirect('deficiencies:detail', deficiency_number=deficiency_number)
    else:
        # GET request - redirect to detail page (action form is embedded there)
        return redirect('deficiencies:detail', deficiency_number=deficiency_number)