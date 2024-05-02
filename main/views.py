from django.shortcuts import render,redirect
from django.views.generic import TemplateView ,ListView,CreateView,View
from .models import logotip,select,gallery,CountryPictures
from .forms import SelectRegistrForm
# Create your views here.

class home(View):
    def get(self,request):
        pic=gallery.objects.all()
        return render(request,'main.html',{'pic':pic})
    
    
class about(TemplateView):
    template_name='about_us.html'
    
class RASMLAR(View):
    def get (self,request):
        galler=gallery.objects.all().order_by('id')
        search_quary=request.GET.get('q','')
        galler=galler.filter(Davlat__icontains=search_quary)
        if search_quary:
            return render(request,'gallery.html',{'gallery':galler,'search':search_quary})
        return render(request,'gallery.html',{'gallery':galler})
    
class Tanlash(CreateView):
    def get(self, request):
        user = SelectRegistrForm()
        return render(request, "select.html", {'form':user})

    def post(self, request):
        user = SelectRegistrForm(data=request.POST)
        if user.is_valid():
            user.save()
            return redirect("gallery")
        else:
            return render(request, "select.html", {'form': user})

class CountryDetailView(View):
    def get(self,request,id):
        country=gallery.objects.filter(id=id)
        pic=CountryPictures.objects.filter(country_id=id)
        return render(request, "countrydetail.html",{'countrypic':pic,'country':country})
    

        
        
