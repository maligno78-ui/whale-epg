# Whale TV+ EPG

Guia EPG XMLTV para canales de Whale TV+. Se actualiza automaticamente cada dia a las 06:00 UTC.

## URL del EPG

```
https://raw.githubusercontent.com/maligno78-ui/whale-epg/main/epg.xml
```

Añade esta URL a tu M3U en la cabecera:

```m3u
#EXTM3U url-tvg="https://raw.githubusercontent.com/maligno78-ui/whale-epg/main/epg.xml"
```

## Como funciona

- Un script Python consulta la API oficial de Whale TV+
- Obtiene la guia de 7 dias para todos los canales
- Genera un archivo XMLTV compatible con IPTV players
- GitHub Actions lo ejecuta cada dia automaticamente
