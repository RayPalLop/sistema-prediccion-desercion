import csv
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.db.models import Count, Q, Max
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from .models import AlertaDesercion, Estudiante, Persona, Carrera

@login_required
def dashboard_alertas(request):
    alertas = AlertaDesercion.objects.select_related('estudiante__persona').all()
    context = {
        'alertas': alertas,
        'total': alertas.count(),
        'alto': alertas.filter(nivel_riesgo='Alto').count(),
        'medio': alertas.filter(nivel_riesgo='Medio').count(),
        'bajo': alertas.filter(nivel_riesgo='Bajo').count(),
    }
    return render(request, 'dashboard/alertas.html', context)

@login_required
def dashboard_home(request):
    total_estudiantes = Estudiante.objects.count()
    total_alertas = AlertaDesercion.objects.count()
    context = {
        'total_estudiantes': total_estudiantes,
        'total_alertas': total_alertas,
    }
    return render(request, 'dashboard/home.html', context)

@login_required
def lista_estudiantes(request):
    query = request.GET.get('q', '')
    estudiantes_list = Estudiante.objects.select_related('persona', 'carrera').all().order_by('-id')
    
    if query:
        estudiantes_list = estudiantes_list.filter(
            Q(persona__primer_nombre__icontains=query) |
            Q(persona__primer_apellido__icontains=query)
        )
        
    paginator = Paginator(estudiantes_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'estudiantes': page_obj,
        'total_estudiantes': estudiantes_list.count(),
        'query': query,
    }
    return render(request, 'dashboard/estudiantes.html', context)

@login_required
def estadisticas(request):
    total_estudiantes = Estudiante.objects.count()
    total_alertas = AlertaDesercion.objects.count()
    riesgos_agrupados = AlertaDesercion.objects.values('nivel_riesgo').annotate(total=Count('estudiante'))
    datos_riesgo = {'Alto': 0, 'Medio': 0, 'Bajo': 0}
    
    for item in riesgos_agrupados:
        nivel = item['nivel_riesgo']
        if nivel in datos_riesgo:
            datos_riesgo[nivel] = item['total']

    context = {
        'total_estudiantes': total_estudiantes,
        'total_alertas': total_alertas,
        'riesgo_alto': datos_riesgo['Alto'],
        'riesgo_medio': datos_riesgo['Medio'],
        'riesgo_bajo': datos_riesgo['Bajo'],
    }
    return render(request, 'dashboard/estadisticas.html', context)

@login_required
def configuracion(request):
    context = {'usuario': request.user}
    return render(request, 'dashboard/configuracion.html', context)

@login_required
def exportar_estudiantes(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="directorio_estudiantes.csv"'
    response.write('\ufeff'.encode('utf8'))
    writer = csv.writer(response)
    writer.writerow(['Nombres', 'Apellidos', 'Carrera', 'Estado'])
    
    estudiantes = Estudiante.objects.select_related('persona', 'carrera').all()
    for est in estudiantes:
        carrera_nombre = est.carrera.nombre if est.carrera else 'Sin asignar'
        writer.writerow([est.persona.primer_nombre, est.persona.primer_apellido, carrera_nombre, 'Activo'])
        
    return response

# --- NUEVA FUNCIÓN: CREAR ESTUDIANTE ---
@login_required
def nuevo_estudiante(request):
    # Traemos las carreras para mostrarlas en el menú desplegable
    carreras = Carrera.objects.all().order_by('nombre')
    
    if request.method == 'POST':
        # 1. Capturamos los datos del formulario HTML
        nombre = request.POST.get('nombre')
        apellido = request.POST.get('apellido')
        carrera_id = request.POST.get('carrera')
        
        # 2. Como la DB es gestionada manualmente, calculamos el próximo ID para Persona
        max_persona = Persona.objects.aggregate(Max('id'))['id__max']
        nuevo_id_persona = (max_persona or 0) + 1
        
        persona = Persona.objects.create(
            id=nuevo_id_persona,
            primer_nombre=nombre,
            primer_apellido=apellido
        )
        
        # 3. Calculamos el próximo ID para Estudiante y enlazamos
        max_est = Estudiante.objects.aggregate(Max('id'))['id__max']
        nuevo_id_est = (max_est or 0) + 1
        carrera_obj = Carrera.objects.get(id=carrera_id)
        
        # Generamos un código temporal automático usando el ID (Ej: EST-0021)
        codigo_generado = f"EST-{nuevo_id_est:04d}"
        
        Estudiante.objects.create(
            id=nuevo_id_est,
            persona=persona,
            carrera=carrera_obj,
            codigo_estudiante=codigo_generado  # Enviamos el dato obligatorio
        )
        
        # 4. Redirigimos a la tabla para ver el nuevo registro
        return redirect('estudiantes')
        
    return render(request, 'dashboard/nuevo_estudiante.html', {'carreras': carreras})