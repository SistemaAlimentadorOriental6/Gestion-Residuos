# models.py

from django.db import models
from django.contrib.auth.models import User



class ResiduoPrecio(models.Model):
    tipo_residuo = models.CharField(max_length=50)
    residuo = models.CharField(max_length=50)
    costo_unitario = models.IntegerField()
    
    class Meta:
        db_table = "residuos_precio"




class GrupoResiduo(models.Model):
    codigo = models.CharField(max_length=100, unique=True)
    creado_por = models.ForeignKey(User, on_delete=models.CASCADE)
    creado_en = models.DateTimeField(auto_now_add=True)
    completado = models.BooleanField(default=False) 

    def __str__(self):
        return self.codigo
    
    class Meta:
        db_table = "grupo_residuo"




class FormularioPerfil1(models.Model):
    fecha = models.DateField(auto_now_add=True)
    hora = models.TimeField(auto_now_add=True)
    tipo_residuo = models.CharField(max_length=100)
    residuo = models.CharField(max_length=100)
    peso_cantidad = models.DecimalField(max_digits=10, decimal_places=1)
    costo_unitario = models.IntegerField()
    costo_total = models.IntegerField()
    grupo_codigo = models.ForeignKey(GrupoResiduo, on_delete=models.CASCADE)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.grupo.codigo} - Perfil 1"

    class Meta:
        db_table = "formulario_perfil1"




class FormularioPerfil2(models.Model):
    fecha = models.DateField(auto_now_add=True)
    hora = models.TimeField(auto_now_add=True)
    tipo_residuo = models.CharField(max_length=50)
    residuo = models.CharField(max_length=100)
    peso_cantidad = models.DecimalField(max_digits=10, decimal_places=1)
    grupo_codigo = models.ForeignKey(GrupoResiduo, on_delete=models.CASCADE)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.grupo.codigo} - Perfil 2"

    class Meta:
        db_table = "formulario_perfil2"




class AutorizacionSalida(models.Model):
    fecha_autorizacion = models.DateTimeField(auto_now_add=True)
    hora = models.TimeField(auto_now_add=True)
    grupo_codigo = models.OneToOneField(GrupoResiduo, on_delete=models.CASCADE)
    estado = models.CharField(max_length=20, choices=[
        ('pendiente', 'Pendiente'),
        ('autorizado', 'Autorizado'),
        ('rechazado', 'Rechazado'),
    ], default='pendiente')
    observacion = models.TextField(blank=True)
    autorizador = models.ForeignKey(User, on_delete=models.CASCADE)
    diferencia = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.grupo.codigo} - {self.estado}"

    class Meta:
        db_table = "autorizacion_salida"
        
        



        

    