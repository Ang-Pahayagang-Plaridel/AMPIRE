from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class APPInfo(models.Model):
    year = models.IntegerField(unique=True)
    sirk_folder_id = models.CharField(max_length=40, null=True, default=None)

class Section(models.Model):
    name = models.CharField(max_length=20)
    full_name = models.CharField(max_length=60)
    section_color = models.CharField(max_length=12)
    # primary_color = models.CharField(max_length=12)
    # secondary_color = models.CharField(max_length=12)
    is_active = models.BooleanField(default=True)

class Member(models.Model):
    id_num = models.IntegerField(unique=True)
    last_name = models.CharField(max_length=150)
    first_name = models.CharField(max_length=150)
    middle_initial = models.CharField(max_length=5, null=True)
    position = models.CharField(max_length=120)
    section = models.ForeignKey(Section, on_delete=models.DO_NOTHING)
    is_active = models.BooleanField(default=True)

    def is_senyor(self) : return "Senyor na " in self.position

    def is_eb(self):
        return not self.is_senyor() and \
           "Kasapi" not in self.position and \
           "Korespondente" not in self.position

    def get_name(self):
        name = f'{self.last_name}, {self.first_name}'
        if self.middle_initial is not None : name = f'{name} {self.middle_initial}.' 
        return name
    
    def get_position(self):
        parts = []

        # if self.is_senyor() : parts.append("Senyor na")

        parts.append(self.position)

        if "Kasapi" in self.position or "Korespondente" in self.position : parts.append(f"ng {self.section.name}")

        return " ".join(parts)
    
    def save(self, *args, **kwargs):
        self.last_name = self.last_name.title()
        self.first_name = self.first_name.title()
        if self.middle_initial:
            self.middle_initial = ' '.join(self.middle_initial).upper()

        
        super(Member, self).save(*args, **kwargs)