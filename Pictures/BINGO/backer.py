import random  
from PIL import Image, ImageDraw, ImageFont  

def generar_carton_bingo():  
    # Genera un cartón de bingo con números únicos  
    carton = []  
    columnas = {  
        'B': random.sample(range(1, 16), 5),     # Números del 1 al 15 para la columna B  
        'I': random.sample(range(16, 31), 5),    # Números del 16 al 30 para la columna I  
        'N': random.sample(range(31, 46), 5),    # Números del 31 al 45 para la columna N  
        'G': random.sample(range(46, 61), 5),    # Números del 46 al 60 para la columna G  
        'O': random.sample(range(61, 76), 5)     # Números del 61 al 75 para la columna O  
    }  

    # Crear la matriz del cartón  
    for i in range(5):  
        carton.append([columnas['B'][i], columnas['I'][i], columnas['N'][i], columnas['G'][i], columnas['O'][i]])  

    # Marcar la casilla central (número libre)  
    carton[2][2] = None  # Este representa el espacio libre  

    return carton  

def generar_cartones(cantidad):  
    # Genera múltiples cartones de bingo  
    return [generar_carton_bingo() for _ in range(cantidad)]  

def mostrar_carton(carton):  
    # Mostrar un solo cartón en la consola  
    print(" B   I   N   G   O")  
    print("-------------------")  
    for fila in carton:  
        for numero in fila:  
            if numero is None:  
                print(" * ", end="")  # Indicar espacio libre  
            else:  
                print(f"{numero:>2} ", end="")  
        print()  
    print("-------------------\n")  

def guardar_carton_imagen(carton, nombre_archivo):  
    # Tamaños de la imagen y celdas  
    ancho_celda = 100  
    alto_celda = 100  
    margen = 10  

    # Crear una imagen en blanco  
    imagen = Image.new('RGB', (ancho_celda * 5 + margen * 6, alto_celda * 5 + margen * 6), 'white')  
    dibujar = ImageDraw.Draw(imagen)  

    # Cargar una fuente (puedes cambiar la ruta de la fuente si es necesario)  
    font = ImageFont.load_default()  

    # Dibujar la tabla del cartón de bingo  
    for i, fila in enumerate(carton):  
        for j, numero in enumerate(fila):  
            x = j * (ancho_celda + margen) + margen  
            y = i * (alto_celda + margen) + margen  
            dibujar.rectangle([x, y, x + ancho_celda, y + alto_celda], outline='black', fill='lightgray')  
            texto = '*' if numero is None else str(numero)  
            text_width, text_height = dibujar.textsize(texto, font)  
            # Centrar el texto  
            dibujar.text((x + (ancho_celda - text_width) / 2, y + (alto_celda - text_height) / 2), texto, fill='black', font=font)  

    # Guardar la imagen  
    imagen.save(nombre_archivo)  
    print(f"Cartón guardado como imagen en '{nombre_archivo}'.")  

def guardar_cartones_como_imagenes(cartones):  
    # Guarda todos los cartones como imágenes  
    for index, carton in enumerate(cartones):  
        nombre_archivo = f'carton_bingo_{index + 1}.png'  
        guardar_carton_imagen(carton, nombre_archivo)  

# Ejemplo de uso  
if __name__ == "__main__":  
    try:  
        cantidad = int(input("¿Cuántos cartones de bingo deseas generar? "))  
        cartones = generar_cartones(cantidad)  
        
        # Mostrar en consola  
        for index, carton in enumerate(cartones):  
            print(f"Cartón {index + 1}:")  
            mostrar_carton(carton)  

        # Guardar los cartones como imágenes  
        guardar_cartones_como_imagenes(cartones)  

    except ValueError:  
        print("Por favor, ingresa un número válido.")
        