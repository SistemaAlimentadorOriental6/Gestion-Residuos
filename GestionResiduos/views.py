from collections import defaultdict
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout
from django.utils.timezone import now
from GestionResiduos.models import FormularioPerfil1, FormularioPerfil2, GrupoResiduo, AutorizacionSalida, ResiduoPrecio
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden
from django.utils.timezone import localtime
from django.utils.safestring import mark_safe
from django.core.serializers.json import DjangoJSONEncoder
import json
from openpyxl.styles import PatternFill, Font, Alignment
from openpyxl import Workbook, load_workbook
from django.http import HttpResponse
from django.conf import settings
import os
from openpyxl.utils import get_column_letter
from django.db.models.functions import ExtractMonth, ExtractYear
from decimal import Decimal



def inicio(request):
    return render(request, 'base.html')




@login_required
def formularioResiduos(request):
    es_sergio = request.user.username == '1036619811'

    TOLERANCIA_PESO = Decimal('10.0')
    TOLERANCIA_CANTIDAD = 5

    grupo = None

    if request.method == 'POST':
        tipo_residuo = request.POST.get('tipo')
        residuo = request.POST.get('residuo')

        peso_raw = request.POST.get('peso')
        cantidad_raw = request.POST.get('cantidad')

        peso = Decimal(peso_raw.replace(',', '.')) if peso_raw else Decimal('0')
        cantidad = int(cantidad_raw) if cantidad_raw else 0

        # Buscar grupo compatible
        posibles_grupos = GrupoResiduo.objects.filter(completado=False)

        for posible in posibles_grupos:
            existe_1 = FormularioPerfil1.objects.filter(grupo_codigo=posible).exists()
            existe_2 = FormularioPerfil2.objects.filter(grupo_codigo=posible).exists()

            if es_sergio and not existe_1:
                perfil2 = FormularioPerfil2.objects.filter(
                    grupo_codigo=posible,
                    tipo_residuo=tipo_residuo,
                    residuo=residuo
                ).first()
                if perfil2 and abs(perfil2.peso - peso) <= TOLERANCIA_PESO and abs(perfil2.cantidad - cantidad) <= TOLERANCIA_CANTIDAD:
                    grupo = posible
                    break

            elif not es_sergio and not existe_2:
                perfil1 = FormularioPerfil1.objects.filter(
                    grupo_codigo=posible,
                    tipo_residuo=tipo_residuo,
                    residuo=residuo
                ).first()
                if perfil1 and abs(perfil1.peso - peso) <= TOLERANCIA_PESO and abs(perfil1.cantidad - cantidad) <= TOLERANCIA_CANTIDAD:
                    grupo = posible
                    break

        # Si no se encontró grupo compatible
        if not grupo:
            if es_sergio:
                messages.error(request, "No se encontró un grupo compatible. Verifica que el vigilante haya registrado el residuo primero.")
                return redirect('formularioResiduos')
            else:
                fecha_hora = localtime(now()).strftime('%Y%m%d%H%M%S')
                codigo = f"GRP-{request.user.id}-{fecha_hora}"
                grupo = GrupoResiduo.objects.create(
                    codigo=codigo,
                    creado_por=request.user
                )

        # Guardar formulario
        if es_sergio:
            costo_unitario = int(request.POST.get('costo_unitario', '0').replace('.', '').replace(',', ''))
            costo_total = int(request.POST.get('costo_total', '0').replace('.', '').replace(',', ''))

            FormularioPerfil1.objects.create(
                tipo_residuo=tipo_residuo,
                residuo=residuo,
                peso=peso,
                cantidad=cantidad,
                costo_unitario=costo_unitario,
                costo_total=costo_total,
                grupo_codigo=grupo,
                usuario=request.user
            )

            if not ResiduoPrecio.objects.filter(residuo=residuo).exists():
                ResiduoPrecio.objects.create(
                    tipo_residuo=tipo_residuo,
                    residuo=residuo,
                    costo_unitario=costo_unitario
                )
        else:
            FormularioPerfil2.objects.create(
                tipo_residuo=tipo_residuo,
                residuo=residuo,
                peso=peso,
                cantidad=cantidad,
                grupo_codigo=grupo,
                usuario=request.user
            )

        # Verificar si el grupo está completo
        perfil1_ok = FormularioPerfil1.objects.filter(grupo_codigo=grupo).exists()
        perfil2_ok = FormularioPerfil2.objects.filter(grupo_codigo=grupo).exists()

        if perfil1_ok and perfil2_ok:
            grupo.completado = True
            grupo.save()

        messages.success(request, "Residuo guardado exitosamente.")
        return redirect('formularioResiduos')

    
    else:
        # GET: preparación de datos
        residuos_precios = ResiduoPrecio.objects.all()
        precios_dict = {r.residuo: r.costo_unitario for r in residuos_precios}
        precios_json = mark_safe(json.dumps(precios_dict, cls=DjangoJSONEncoder))

        grupos_pendientes = []
        if es_sergio:
            grupos_incompletos = GrupoResiduo.objects.filter(
                completado=False,
                formularioperfil1__isnull=True,
                formularioperfil2__isnull=False
            ).distinct()

            for grupo in grupos_incompletos:
                registro_vigilancia = FormularioPerfil2.objects.filter(grupo_codigo=grupo).first()
                if registro_vigilancia:
                    grupos_pendientes.append({
                        'codigo': grupo.codigo,
                        'fecha': registro_vigilancia.fecha,
                        'tipo': registro_vigilancia.tipo_residuo,
                        'residuo': registro_vigilancia.residuo,
                    })

        return render(request, 'Residuos/formulario.html', {
            'es_sergio': es_sergio,
            'grupo_codigo': "",
            'precios_residuos_json': precios_json,
            'grupos_pendientes': grupos_pendientes
        })



@login_required
def listadoAutorizaciones(request):
    if request.user.username != '1112629169':
        return HttpResponseForbidden("No tienes permiso para ver esta página.")

    grupos = GrupoResiduo.objects.filter(completado=True).exclude(autorizacionsalida__isnull=False)
    grupos_alerta = []

    baterias_keywords = ['bateria', 'batería', 'und']

    for grupo in grupos:
        registros_p1 = grupo.formularioperfil1_set.all()
        registros_p2 = grupo.formularioperfil2_set.all()

        residuos_data = defaultdict(lambda: {'perfil1': 0, 'perfil2': 0, 'modo': 'peso'})

        for r in registros_p1:
            key = r.residuo.lower().strip()
            modo = 'cantidad' if any(k in key for k in baterias_keywords) else 'peso'
            valor_p1 = r.cantidad if modo == 'cantidad' else float(r.peso or 0)
            residuos_data[key]['perfil1'] += valor_p1
            residuos_data[key]['modo'] = modo

        for r in registros_p2:
            key = r.residuo.lower().strip()
            modo = 'cantidad' if any(k in key for k in baterias_keywords) else 'peso'
            valor_p2 = r.cantidad if modo == 'cantidad' else float(r.peso or 0)
            residuos_data[key]['perfil2'] += valor_p2
            residuos_data[key]['modo'] = modo

        diferencias = []
        for residuo, datos in residuos_data.items():
            v1, v2 = datos['perfil1'], datos['perfil2']
            modo = datos['modo']

            if modo == 'cantidad':
                if v1 != v2:
                    diferencias.append({
                        'residuo': residuo,
                        'modo': 'Cantidad',
                        'valor_p1': v1,
                        'valor_p2': v2,
                        'mensaje': v1 - v2
                    })
            else:  
                if v1 or v2:
                    referencia = v1 if v1 else 1  # Usa perfil1 como base
                    dif_pct = abs(v1 - v2) / referencia * 100
                    if dif_pct > 5:
                        diferencias.append({
                            'residuo': residuo,
                            'modo': 'Peso',
                            'valor_p1': v1,
                            'valor_p2': v2,
                            'diferencia_pct': round(dif_pct, 2)
                        })

        grupos_alerta.append({
            'grupo': grupo,
            'diferencias': diferencias,
            'alerta': bool(diferencias)
        })

    if request.method == 'POST':
        grupo_id = request.POST.get('grupo_id')
        estado = request.POST.get('estado')
        observacion = request.POST.get('observacion', '')
        alerta_peso = request.POST.get('alerta_peso', '')
        print(f"Alerta peso recibida: {alerta_peso}")
        
        diferencia = ""
        if alerta_peso:
            diferencia = alerta_peso
            print(f"La novedad es por el peso: {diferencia}")
            
        else:
            alerta_cant = request.POST.get('alerta_cant', '')
            print(f"Alerta cantidad recibida: {alerta_cant}")
            diferencia = alerta_cant
            print(f"La novedad es por la cantidad: {diferencia}")

        
        grupo = get_object_or_404(GrupoResiduo, id=grupo_id)

        AutorizacionSalida.objects.create(
            grupo_codigo=grupo,
            estado=estado,
            observacion=observacion or "Ninguna",
            autorizador=request.user,
            diferencia=diferencia or "Ninguna",         
        )

        messages.success(request, f'Grupo {grupo.codigo} autorizado correctamente.')
        return redirect('listadoAutorizaciones')

    return render(request, 'residuos/listadoAutorizaciones.html', {
        'grupos_alerta': grupos_alerta
    })





@login_required
def registrosVigilantes(request):
    registros = FormularioPerfil2.objects.filter(usuario=request.user).order_by('-fecha', '-hora')
    return render(request, 'Residuos/registrosVigilantes.html', {'registros': registros})



@login_required
def registrosSergio(request):
    registros = FormularioPerfil1.objects.filter(usuario=request.user).order_by('-fecha', '-hora')
    return render(request, 'Residuos/registrosSergio.html', {'registros': registros})




def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)
            if user.username == '1112629169':  
                return redirect('listadoAutorizaciones')
            else:  
                return redirect('formularioResiduos')

        else:
            messages.error(request, 'Credenciales inválidas')
    return render(request, 'Login/login.html')




def logout_view(request):
    logout(request)
    return redirect('login')



@login_required
def agregarResiduoPrecio(request):
    if request.method == 'POST':
        tipo_residuo = request.POST['tipo_residuo']
        residuo = request.POST['residuo']
        costo_unitario = int(request.POST.get('costo_unitario', '0').replace('.', '').replace(',', ''))
        
        residuo_costo = ResiduoPrecio.objects.create(
            tipo_residuo = tipo_residuo,
            residuo = residuo,
            costo_unitario = costo_unitario,
        )
        
        residuo_costo.save()
        
        messages.success(request, "Residuo y precio guardado exitosamente")
        return redirect('agregarResiduoPrecio')
    
    return render(request, "Residuos/agregarResiduo.html")




@login_required
def listadoResiduosPrecios(request):
    residuos_precios = ResiduoPrecio.objects.all()
    return render(request, "Residuos/listadoResiduos.html", {'residuos_precios' : residuos_precios})




@login_required
def actualizarResiduoPrecio(request, id):
    residuo_obj = get_object_or_404(ResiduoPrecio, id=id)
    if request.method == 'POST':
        tipo_residuo = request.POST['tipo_residuo']
        residuo = request.POST['residuo']
        costo_unitario = int(request.POST.get('costo_unitario', '0').replace('.', '').replace(',', ''))
        
        residuo_obj.tipo_residuo = tipo_residuo
        residuo_obj.residuo = residuo
        residuo_obj.costo_unitario = costo_unitario
        residuo_obj.save()
        
        residuo_obj.save()
        
        messages.success(request, "Residuo y precio guardado exitosamente")
        return redirect('listadoResiduosPrecio')
    
    return render(request, 'Residuos/actualizarResiduo.html', {
        'residuo': residuo_obj
    })




@login_required
def actualizarCostoTotal(request, registro_id):
    registro = get_object_or_404(FormularioPerfil1, id=registro_id)

    if request.method == 'POST':
        try:
            campo = request.POST.get('campo_modificado')

            costo_raw = request.POST.get('costo_total', '').replace('.', '').replace(',', '.')
            nuevo_costo = float(costo_raw) if costo_raw else 0

            peso_raw = request.POST.get('peso', '')
            peso_val = float(peso_raw.replace('.', '').replace(',', '.')) if peso_raw else 0

            if campo == 'peso':
                registro.peso = peso_val
                registro.costo_total = round(peso_val * registro.costo_unitario)

            elif campo == 'costo_total':
                registro.costo_total = round(nuevo_costo)

            registro.save()
            messages.success(request, "Registro actualizado correctamente.")

        except Exception as e:
            messages.error(request, f"Error al actualizar: {str(e)}")

    return redirect('registrosSergio')



def generarExcel(request, registro_id):
    registro_base = FormularioPerfil1.objects.get(pk=registro_id)
    fecha_base = registro_base.fecha

    mes = fecha_base.month
    año = fecha_base.year
    meses = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
        5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
        9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }

    nombre_archivo = f'Consolidado PMIRS {meses[mes]} {año}.xlsx'
    file_path = os.path.join(settings.MEDIA_ROOT, nombre_archivo)

    registros = FormularioPerfil1.objects.annotate(
        mes=ExtractMonth('fecha'),
        anio=ExtractYear('fecha')
    ).filter(mes=mes, anio=año)

    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

    if not os.path.exists(file_path):
        wb = Workbook()
        ws = wb.active
        ws.title = "Consolidados"
        encabezados = ["Tipo_Residuo", "Residuo", "Fecha", "Peso", "Cantidad", "Costo_Unitario", "Costo_Total"]

        estilo = {
            "fill": PatternFill(start_color="6BA43A", end_color="6BA43A", fill_type="solid"),
            "font": Font(color="000000", bold=True),
            "alignment": Alignment(horizontal="center")
        }

        for col_num, encabezado in enumerate(encabezados, 1):
            cell = ws.cell(row=1, column=col_num, value=encabezado)
            cell.fill = estilo["fill"]
            cell.font = estilo["font"]
            cell.alignment = estilo["alignment"]

        wb.save(file_path)

    wb = load_workbook(file_path)
    ws = wb.active
    registros_guardados = set()

    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[1] and row[2]:  # residuo y fecha
            registros_guardados.add((row[1], row[2]))  # clave sin hora

    fila_excel = ws.max_row + 1
    for reg in registros:
        fecha_str = reg.fecha.strftime('%d-%m-%y')
        clave = (reg.residuo, fecha_str)

        if clave in registros_guardados:
            continue

        fila = [
            reg.tipo_residuo,
            reg.residuo,
            fecha_str,
            float(reg.peso),
            float(reg.cantidad),
            float(reg.costo_unitario),
            float(reg.costo_total)
        ]

        for col_idx, valor in enumerate(fila, 1):
            cell = ws.cell(row=fila_excel, column=col_idx, value=valor)
            cell.alignment = Alignment(horizontal="center")
            if col_idx in [6, 7]:  # Costo_Unitario y Costo_Total
                cell.number_format = '#,##0'    

        fila_excel += 1

    # Ajustar ancho de columnas según contenido
    for col in ws.columns:
        max_length = 0
        column = col[0].column  # número de columna
        column_letter = get_column_letter(column)

        for cell in col:
            if cell.value:
                max_length = max(max_length, len(str(cell.value)))

        ws.column_dimensions[column_letter].width = max_length + 2

    wb.save(file_path)

    with open(file_path, 'rb') as f:
        response = HttpResponse(
            f.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'inline; filename="{nombre_archivo}"'
        return response
    
    
    
    
    
