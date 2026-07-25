from .cart import Cart


def cart(request):
    """Make the cart available in all templates as {{ cart }}."""
    return {'cart': Cart(request)}
