import qrcode

upi_string = "upi://pay?pa=7676026106-gc0b@axl&pn=Charity&am=100"

img = qrcode.make(upi_string)
img.save("static/upi_qr/upi_100.png")
