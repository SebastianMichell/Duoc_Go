from django.shortcuts import redirect
from django.urls import reverse

class RoleRestrictionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        
        if not request.user.is_authenticated:
            return self.get_response(request)

        path = request.path
        role = request.user.tipo_usuario

        if path.startswith('/static/') or path.startswith('/media/') or path == reverse('logout'):
            return self.get_response(request)

        if role == 'local':
            is_allowed_path = (
                path.startswith(reverse('local:panel')) or 
                path.startswith('/admin/')
            )
            
            if not is_allowed_path:
                return redirect('local:panel')

        elif role == 'estudiante':
            is_restricted_path = (
                path.startswith(reverse('local:panel')) or 
                path.startswith('/admin/')
            )
            
            if is_restricted_path:
                return redirect('home')
        
        return self.get_response(request)