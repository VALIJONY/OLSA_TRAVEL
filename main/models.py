from django.db import models

class logotip(models.Model):
    logo=models.ImageField(default='body_fon.jpg')
# Create your models here.
class gallery(models.Model):
    Davlat=models.CharField(max_length=100)
    rasm=models.ImageField()
    malumot=models.TextField()
    narxi=models.IntegerField()
    
    def __str__(self):
         return self.Davlat
     
class CountryPictures(models.Model):
    picture=models.ImageField()
    country_id=models.ForeignKey(gallery,on_delete=models.CASCADE)
     
    
class select(models.Model):
    Ism=models.CharField(max_length=100)
    Familiya=models.CharField(max_length=100)
    Telefon_raqam=models.CharField(max_length=100)
    Sayohat_joyini_tanlang=models.ForeignKey(gallery,on_delete=models.CASCADE)
    