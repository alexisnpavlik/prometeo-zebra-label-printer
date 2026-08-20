#!/usr/bin/env bash
# Instala Etiquetas Zebra en el menu de aplicaciones de Linux.
#
# Uso:
#   ./instalar-linux.sh [ruta-al-ejecutable]
#   ./instalar-linux.sh --desinstalar
#
# Sin argumentos busca el ejecutable junto a este script o en ~/Descargas.
# Todo se instala en el home del usuario: no pide sudo.

set -euo pipefail

DESTINO="$HOME/.local/share/etiquetas-zebra"
LANZADOR="$HOME/.local/share/applications/etiquetas-zebra.desktop"
ICONO="$HOME/.local/share/icons/hicolor/256x256/apps/etiquetas-zebra.png"
AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

desinstalar() {
    rm -rf "$DESTINO"
    rm -f "$LANZADOR" "$ICONO"
    actualizar_menu
    echo "Desinstalado. La configuracion en $DESTINO tambien se borro."
}

actualizar_menu() {
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
    fi
    if command -v gtk-update-icon-cache >/dev/null 2>&1; then
        gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
    fi
}

buscar_ejecutable() {
    local candidato
    for candidato in \
        "$AQUI/etiquetas-zebra-linux" \
        "$AQUI/dist/etiquetas-zebra" \
        "$HOME/Descargas/etiquetas-zebra-linux" \
        "$HOME/Downloads/etiquetas-zebra-linux"
    do
        if [ -f "$candidato" ]; then
            echo "$candidato"
            return 0
        fi
    done
    return 1
}

if [ "${1:-}" = "--desinstalar" ]; then
    desinstalar
    exit 0
fi

if [ $# -ge 1 ]; then
    EJECUTABLE="$1"
else
    if ! EJECUTABLE="$(buscar_ejecutable)"; then
        echo "No encontre el ejecutable." >&2
        echo "Bajalo de los releases y pasame la ruta:" >&2
        echo "  ./instalar-linux.sh ~/Descargas/etiquetas-zebra-linux" >&2
        exit 1
    fi
fi

if [ ! -f "$EJECUTABLE" ]; then
    echo "No existe: $EJECUTABLE" >&2
    exit 1
fi

mkdir -p "$DESTINO" "$(dirname "$LANZADOR")" "$(dirname "$ICONO")"

# el config.json queda junto al ejecutable, asi que se instala en su propia carpeta
install -m 755 "$EJECUTABLE" "$DESTINO/etiquetas-zebra"

# el icono puede venir del repo o suelto junto al script, si se bajo del release
if [ -f "$AQUI/docs/img/icono.png" ]; then
    install -m 644 "$AQUI/docs/img/icono.png" "$ICONO"
elif [ -f "$AQUI/icono.png" ]; then
    install -m 644 "$AQUI/icono.png" "$ICONO"
else
    echo "Aviso: no encontre el icono, el lanzador va sin icono propio." >&2
fi

cat > "$LANZADOR" <<DESKTOP
[Desktop Entry]
Type=Application
Name=Etiquetas Zebra
GenericName=Impresion de etiquetas
Comment=Imprime etiquetas de producto en Zebra desde el TXT de Odoo
Exec=$DESTINO/etiquetas-zebra
Path=$DESTINO
Icon=etiquetas-zebra
Terminal=false
Categories=Office;Printing;
Keywords=zebra;etiquetas;codigo de barras;odoo;prometeo;
StartupNotify=true
DESKTOP

chmod 644 "$LANZADOR"
actualizar_menu

echo "Instalado en $DESTINO"
echo "Buscalo como \"Etiquetas Zebra\" en el menu de aplicaciones."
