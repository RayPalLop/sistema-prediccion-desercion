from django.db import models

# 1. Definimos la tabla Persona
class Persona(models.Model):
    id = models.IntegerField(primary_key=True, db_column='id')
    primer_nombre = models.CharField(max_length=255, db_column='primer_nombre') 
    primer_apellido = models.CharField(max_length=255, db_column='primer_apellido') 

    class Meta:
        db_table = 'persona'
        managed = False

    @property
    def nombre_completo(self):
        return f"{self.primer_nombre} {self.primer_apellido}"

# --- NUEVA CLASE: Mapeamos la tabla de Carreras ---
class Carrera(models.Model):
    id = models.IntegerField(primary_key=True, db_column='id')
    nombre = models.CharField(max_length=255, db_column='nombre')

    class Meta:
        db_table = 'carrera'
        managed = False

# 2. Definimos la tabla Estudiante conectada a Persona y a Carrera
class Estudiante(models.Model):
    id = models.IntegerField(primary_key=True, db_column='id')
    persona = models.ForeignKey(Persona, on_delete=models.DO_NOTHING, db_column='id_persona')
    carrera = models.ForeignKey(Carrera, on_delete=models.DO_NOTHING, db_column='id_carrera', null=True)
    
    # --- NUEVA LÍNEA: Mapeamos el código del estudiante para evitar el IntegrityError ---
    codigo_estudiante = models.CharField(max_length=50, db_column='codigo_estudiante')

    class Meta:
        db_table = 'estudiante'
        managed = False 

# 3. La tabla de Alertas
class AlertaDesercion(models.Model):
    id = models.AutoField(primary_key=True, db_column='id')
    estudiante = models.ForeignKey(
        Estudiante, 
        on_delete=models.DO_NOTHING, 
        db_column='id_estudiante'
    )
    nivel_riesgo = models.CharField(max_length=20)
    color_semaforo = models.CharField(max_length=20, null=True, blank=True)
    causa_ia = models.TextField()

    class Meta:
        db_table = 'alerta_desercion'
        managed = False