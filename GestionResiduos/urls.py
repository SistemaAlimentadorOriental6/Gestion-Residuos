"""
URL configuration for GestionResiduos project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from GestionResiduos.views import formularioResiduos, login_view, logout_view, listadoAutorizaciones, registrosVigilantes, registrosSgi, agregarResiduoPrecio, listadoResiduosPrecios, actualizarResiduoPrecio, actualizarCostoTotal, actualizarRegistroVigilante, generarExcel

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', login_view, name='login'),
    path('residuos/formularioResiduos', formularioResiduos, name='formularioResiduos'),
    path('residuos/listadoAutorizaciones', listadoAutorizaciones, name='listadoAutorizaciones'),
    path('residuos/registrosVigilantes', registrosVigilantes, name='registrosVigilantes'),
    path('residuos/registrosSgi', registrosSgi, name='registrosSgi'),
    path('logout/', logout_view, name='logout'),
    path('residuos/agregarResiduosPrecio', agregarResiduoPrecio, name='agregarResiduoPrecio'),
    path('residuos/listadoResiduosPrecio', listadoResiduosPrecios, name='listadoResiduosPrecio'),
    path('residuos/actualizarResiduo/<int:id>/', actualizarResiduoPrecio , name='actualizarResiduoPrecio'),
    path('residuos/actualizarCostoTotal/<int:registro_id>/', actualizarCostoTotal, name='actualizarCostoTotal'),
    path('residuos/actualizarRegistroVigilante/<int:registro_id>/', actualizarRegistroVigilante, name='actualizarRegistroVigilante'),
    path('residuos/generarExcel/<int:registro_id>/', generarExcel, name='generarExcel'),
]
