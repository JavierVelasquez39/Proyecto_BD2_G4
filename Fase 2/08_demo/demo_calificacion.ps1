# Demostración en vivo de la Fase 2 (carga por deportista, Usain Bolt).
#
# Uso, desde PowerShell 5.1:
#   cd "Fase 2\08_demo"
#   powershell -NoProfile -ExecutionPolicy Bypass -File .\demo_calificacion.ps1
#
# La demo usa su propio proyecto de Docker Compose (fase2_demo) y el override
# docker-compose.demo.yml, que monta 08_demo\salida encima de /fase2/05_logs.
# Así los scripts compartidos escriben sus logs y su CSV de tiempos en
# 08_demo\salida y nunca en 05_logs. La opción A solo lee la evidencia oficial.

$ErrorActionPreference = "Continue"

$Proyecto      = "fase2_demo"
$ProyectoOfic  = "fase2_deportista"
$Raiz          = Split-Path -Parent $PSScriptRoot
$Infra         = Join-Path $Raiz "00_infraestructura"
$Salida        = Join-Path $PSScriptRoot "salida"
$Centinela     = Join-Path $Salida ".salida_demo"
$CsvDemo       = Join-Path $Salida "tiempos_deportista_pc.csv"
$LogsDemo      = Join-Path $Salida "deportista_pc"
$CsvOficial    = Join-Path $Raiz "05_logs\tiempos_deportista_pc.csv"
$LogsOficial   = Join-Path $Raiz "05_logs\deportista_pc"
$CapOficial    = Join-Path $Raiz "06_evidencias\deportista_pc"
$ComposeBase   = @("compose", "-p", $Proyecto, "-f", "docker-compose.yml", "-f", "..\08_demo\docker-compose.demo.yml")
$Rondas        = @("r1_atenas2004", "r2_pekin2008", "r3_londres2012")
$OrdenTablas   = @("pais", "poblacion_pais", "noc", "sede", "edicion_olimpica", "deporte",
                   "deporte_equivalencia", "evento", "atleta", "participacion", "resultado")
# Conteos esperados (02_carga/README.md y RUNBOOK_deportista_pc.md), en el orden de conteos.sql
$ConteosEsperados = @{
  "base"           = @(204, 13026, 236, 0, 0, 95, 2, 0, 0, 0, 0)
  "r1_atenas2004"  = @(204, 13026, 236, 1, 1, 95, 2, 1, 1, 1, 1)
  "r2_pekin2008"   = @(204, 13026, 236, 2, 2, 95, 2, 3, 1, 4, 4)
  "r3_londres2012" = @(204, 13026, 236, 3, 3, 95, 2, 3, 1, 7, 7)
}

$script:Pausas = [System.Diagnostics.Stopwatch]::new()

# ---------------------------------------------------------------- utilidades

function Detener([string]$Mensaje) {
  if ($Mensaje) { Write-Host $Mensaje -ForegroundColor Red }
  Write-Host "FALLO. No repitas nada." -ForegroundColor Red
  exit 1
}

function Confirmar-Proyecto {
  if ($Proyecto -ne "fase2_demo") {
    Write-Host "El proyecto configurado es '$Proyecto' y no 'fase2_demo'. Me niego a continuar." -ForegroundColor Red
    exit 1
  }
}

function Formatear([string[]]$Partes) {
  ($Partes | ForEach-Object { if ($_ -match '[\s;|&<>]' -or $_ -eq "") { '"' + $_ + '"' } else { $_ } }) -join " "
}

function Texto-Comando([string[]]$Cmd) { "docker " + (Formatear ($ComposeBase + $Cmd)) }

# Ejecuta docker compose -p fase2_demo ... y se detiene si el código de salida no es 0.
function X([string[]]$Cmd, [switch]$Capturar) {
  Confirmar-Proyecto
  $todo = $ComposeBase + $Cmd
  if ($Capturar) {
    $out = & docker @todo
    if ($LASTEXITCODE -ne 0) { $out | ForEach-Object { Write-Host $_ }; Detener "Código de salida $LASTEXITCODE en: $(Texto-Comando $Cmd)" }
    return $out
  }
  & docker @todo
  if ($LASTEXITCODE -ne 0) { Detener "Código de salida $LASTEXITCODE en: $(Texto-Comando $Cmd)" }
}

function Pausa([string]$Texto = "Enter para ejecutar") {
  $script:Pausas.Start()
  [void](Read-Host $Texto)
  $script:Pausas.Stop()
}

# Imprime título, qué se comprueba y los comandos; espera Enter; ejecuta.
# Con -SinEjecutar solo muestra los comandos; los ejecuta el bloque $Despues.
function Paso([int]$Num, [string]$Titulo, [string]$Comprueba, [object[]]$Comandos, [scriptblock]$Despues, [switch]$SinEjecutar) {
  Write-Host ""
  Write-Host ("=" * 78) -ForegroundColor DarkGray
  Write-Host "PASO ${Num}: $Titulo" -ForegroundColor Cyan
  Write-Host "Qué se comprueba: $Comprueba" -ForegroundColor Yellow
  Write-Host "Comandos:" -ForegroundColor DarkGray
  foreach ($c in $Comandos) { Write-Host "  $(Texto-Comando $c)" }
  Pausa
  if (-not $SinEjecutar) {
    foreach ($c in $Comandos) {
      Write-Host "> $(Texto-Comando $c)" -ForegroundColor DarkGray
      X $c
    }
  }
  if ($Despues) { & $Despues }
}

function Lineas-Csv([string]$Ruta) {
  if (-not (Test-Path -LiteralPath $Ruta)) { return 0 }
  return [System.IO.File]::ReadAllLines($Ruta).Count
}

function Verificar-Lineas([int]$Esperadas) {
  $hay = Lineas-Csv $CsvDemo
  if ($hay -ne $Esperadas) {
    Detener "El CSV de la demo tiene $hay líneas y se esperaban $Esperadas ($CsvDemo)."
  }
  Write-Host "CSV de la demo: $hay líneas (encabezado + $($hay - 1) filas), lo esperado." -ForegroundColor Green
}

function Verificar-Conteos([string]$Clave) {
  $out = X @("exec", "-T", "-u", "postgres", "db", "psql", "-X", "-At", "-d", "olimpiadas", "-f", "/fase2/04_restauracion/conteos.sql") -Capturar
  $esp = $ConteosEsperados[$Clave]
  $mal = 0
  Write-Host ("{0,-22} {1,8} {2,9}" -f "tabla", "filas", "esperado")
  for ($i = 0; $i -lt $OrdenTablas.Count; $i++) {
    $linea = ($out | Where-Object { $_ -like "$($OrdenTablas[$i])|*" } | Select-Object -First 1)
    $filas = if ($linea) { [int]($linea.Split("|")[1]) } else { -1 }
    $marca = if ($filas -eq $esp[$i]) { "" } else { $mal++; "  <- DISTINTO" }
    Write-Host ("{0,-22} {1,8} {2,9}{3}" -f $OrdenTablas[$i], $filas, $esp[$i], $marca)
  }
  if ($mal -gt 0) { Detener "Los conteos después de '$Clave' no coinciden con lo esperado." }
  Write-Host "Conteos después de '$Clave': iguales a lo esperado." -ForegroundColor Green
}

# Comprueba, sin crear nada, que el override monta 08_demo\salida en /fase2/05_logs.
function Verificar-Montaje {
  Confirmar-Proyecto
  $json = (& docker @($ComposeBase + @("config", "--format", "json"))) -join "`n"
  if ($LASTEXITCODE -ne 0) { Detener "docker compose config falló." }
  $cfg = $json | ConvertFrom-Json
  $vol = $cfg.services.db.volumes | Where-Object { $_.target -eq "/fase2/05_logs" }
  $esperado = (Resolve-Path -LiteralPath $Salida).Path
  if (-not $vol -or ($vol.source.TrimEnd("\") -ne $esperado.TrimEnd("\"))) {
    Detener "El override no monta $esperado en /fase2/05_logs. No se ejecuta nada."
  }
  Write-Host "Montaje verificado: $esperado -> /fase2/05_logs" -ForegroundColor Green
}

function Preparar-Salida {
  if (-not (Test-Path -LiteralPath $Salida)) { New-Item -ItemType Directory -Path $Salida | Out-Null }
  if (-not (Test-Path -LiteralPath $Centinela)) { [System.IO.File]::WriteAllText($Centinela, "salida de la demo`n") }
}

function Recursos-Demo {
  $c = @(docker ps -a -q --filter "label=com.docker.compose.project=$Proyecto")
  $v = @(docker volume ls -q --filter "label=com.docker.compose.project=$Proyecto")
  return @{ Contenedores = @($c | Where-Object { $_ }); Volumenes = @($v | Where-Object { $_ }) }
}

function Ruta-LogRestauracion([int]$N, [int]$Rep) {
  Join-Path $LogsDemo ("deportista_pc_{0:D2}_restore_cadena{1}_rep{2}.log" -f (12 + $N), $N, $Rep)
}

function Mostrar-Diff([int]$N, [int]$Rep) {
  $log = Ruta-LogRestauracion $N $Rep
  if (-not (Test-Path -LiteralPath $log)) { Detener "No existe el log $log." }
  $contenido = Get-Content -LiteralPath $log -Encoding UTF8
  # Solo las líneas de diff -u: cabeceras y "tabla|filas" con signo
  $diff = @($contenido | Where-Object { $_ -match '^(--- /backups/|\+\+\+ /tmp/|[-+][a-z_]+\|\d+$)' })
  $ok = @($contenido | Where-Object { $_ -like "VALIDACION OK*" })
  $fin = @($contenido | Where-Object { $_ -like "=== Restauración*finalizada*" })
  $ref = if ($N -eq 0) { "conteos_full.txt" } else { "conteos_incr$N.txt" }
  Write-Host "Cadena n=$N rep=${Rep}: diff de conteos contra /backups/$ref" -ForegroundColor Cyan
  if ($diff.Count -eq 0) { Write-Host "  sin diferencias (diff no imprimió nada)" -ForegroundColor Green }
  else { $diff | ForEach-Object { Write-Host "  $_" -ForegroundColor Red } }
  $ok + $fin | ForEach-Object { Write-Host "  $_" }
  if ($diff.Count -gt 0 -or $ok.Count -eq 0) { Detener "La restauración n=$N rep=$Rep no validó." }
}

function Comandos-Restaurar([int]$N, [int]$Rep) {
  @(
    , @("stop", "db")
    , @("run", "--rm", "--no-deps", "-T", "-u", "postgres", "--entrypoint", "bash", "db",
        "/fase2/04_restauracion/restaurar.sh", "deportista", "pc", "$N", "$Rep", "demo")
  )
}

# ---------------------------------------------------------------- opción A

function Opcion-A {
  Write-Host ""
  Write-Host "OPCIÓN A: evidencia oficial de $ProyectoOfic (solo lectura)" -ForegroundColor Cyan
  Write-Host "Qué se comprueba: que la corrida oficial existe, completa y sin alertas. Nada se escribe ni se borra." -ForegroundColor Yellow
  $cmds = @(
    "docker ps -a --filter label=com.docker.compose.project=$ProyectoOfic",
    "docker volume ls --filter label=com.docker.compose.project=$ProyectoOfic",
    "Import-Csv ..\05_logs\tiempos_deportista_pc.csv | Group-Object operacion,etapa",
    "Get-ChildItem ..\05_logs\deportista_pc, ..\06_evidencias\deportista_pc",
    "docker run --rm --network none -v ${ProyectoOfic}_backups:/b:ro postgres:17 du -sb /b/full /b/incr1 /b/incr2 /b/incr3",
    "Compare-Object (09 vs 16 de fragmentacion_tablas.csv y fragmentacion_indices.csv)"
  )
  Write-Host "Comandos:" -ForegroundColor DarkGray
  $cmds | ForEach-Object { Write-Host "  $_" }
  Pausa

  Write-Host "`n-- Contenedores y volúmenes de $ProyectoOfic" -ForegroundColor Cyan
  docker ps -a --filter "label=com.docker.compose.project=$ProyectoOfic" --format "table {{.Names}}`t{{.Status}}`t{{.Image}}"
  docker volume ls --filter "label=com.docker.compose.project=$ProyectoOfic"

  Write-Host "`n-- CSV oficial: $CsvOficial" -ForegroundColor Cyan
  if (-not (Test-Path -LiteralPath $CsvOficial)) { Write-Host "No existe el CSV oficial." -ForegroundColor Red }
  else {
    $lineas = Lineas-Csv $CsvOficial
    $filas = Import-Csv -LiteralPath $CsvOficial -Encoding UTF8
    Write-Host "Líneas: $lineas (encabezado + $($filas.Count) filas). Esperado: 53."
    $cult = [System.Globalization.CultureInfo]::InvariantCulture
    $filas | Group-Object operacion, etapa | ForEach-Object {
      $seg = $_.Group | ForEach-Object { [double]::Parse($_.segundos, $cult) }
      $m = $seg | Measure-Object -Average -Minimum -Maximum
      [pscustomobject]@{
        "operacion, etapa" = $_.Name
        filas              = $_.Count
        "seg prom"         = [math]::Round($m.Average, 3)
        "seg min"          = $m.Minimum
        "seg max"          = $m.Maximum
      }
    } | Format-Table -AutoSize | Out-String | Write-Host
    Write-Host "Validación:" ; $filas | Group-Object validacion | ForEach-Object {
      $nombre = if ($_.Name) { $_.Name } else { "(vacía, filas de respaldo y etapas sin validación)" }
      Write-Host ("  {0,-55} {1}" -f $nombre, $_.Count)
    }
    $alertas = @($filas | Where-Object { $_.validacion -eq "ALERTA" }).Count
    Write-Host "Filas con ALERTA: $alertas" -ForegroundColor $(if ($alertas -eq 0) { "Green" } else { "Red" })
  }

  Write-Host "`n-- Logs y capturas" -ForegroundColor Cyan
  if (Test-Path -LiteralPath $LogsOficial) {
    $todos = @(Get-ChildItem -LiteralPath $LogsOficial -File)
    $rotados = @($todos | Where-Object { $_.Name -match '\.\d{8}_\d{6}\.log$' })
    Write-Host "05_logs\deportista_pc: $($todos.Count) archivos, $(@($todos | Where-Object Extension -eq '.log').Count) .log, $($rotados.Count) logs rotados"
  } else { Write-Host "No existe $LogsOficial" -ForegroundColor Red }
  if (Test-Path -LiteralPath $CapOficial) {
    Write-Host "06_evidencias\deportista_pc: $(@(Get-ChildItem -LiteralPath $CapOficial -File -Filter *.png).Count) capturas PNG"
  } else { Write-Host "No existe $CapOficial" -ForegroundColor Red }

  Write-Host "`n-- Tamaño de los respaldos dentro de ${ProyectoOfic}_backups (montado de solo lectura)" -ForegroundColor Cyan
  docker run --rm --network none -v "${ProyectoOfic}_backups:/b:ro" postgres:17 du -sb /b/full /b/incr1 /b/incr2 /b/incr3
  if ($LASTEXITCODE -ne 0) { Write-Host "No se pudo leer el volumen ${ProyectoOfic}_backups." -ForegroundColor Red }

  Write-Host "`n-- Fragmentación antes (paso 09) y después (paso 16)" -ForegroundColor Cyan
  foreach ($tipo in "tablas", "indices") {
    $a = Join-Path $LogsOficial "deportista_pc_09_fragmentacion_$tipo.csv"
    $b = Join-Path $LogsOficial "deportista_pc_16_fragmentacion_$tipo.csv"
    if (-not ((Test-Path -LiteralPath $a) -and (Test-Path -LiteralPath $b))) { Write-Host "Falta $a o $b" -ForegroundColor Red; continue }
    $dif = Compare-Object (Get-Content -LiteralPath $a) (Get-Content -LiteralPath $b)
    if ($dif) { Write-Host "fragmentacion_${tipo}: DISTINTOS" -ForegroundColor Red; $dif | Format-Table -AutoSize | Out-String | Write-Host }
    else { Write-Host "fragmentacion_${tipo}: idénticos ($(@(Get-Content -LiteralPath $a).Count) líneas)" -ForegroundColor Green }
  }
  Write-Host "`nFin de la opción A. No se modificó nada." -ForegroundColor Green
}

# ---------------------------------------------------------------- opción B

function Opcion-B {
  Confirmar-Proyecto
  $r = Recursos-Demo
  if ($r.Contenedores.Count -gt 0 -or $r.Volumenes.Count -gt 0) {
    Write-Host "Ya existe el proyecto $Proyecto ($($r.Contenedores.Count) contenedores, $($r.Volumenes.Count) volúmenes)." -ForegroundColor Red
    Write-Host "Usa la opción D para limpiarlo antes de repetir el ciclo completo." -ForegroundColor Red
    return
  }
  # La salida de la demo se vacía para que el conteo de líneas del CSV parta de cero.
  if ((Split-Path -Leaf $Salida) -ne "salida" -or (Split-Path -Leaf (Split-Path -Parent $Salida)) -ne "08_demo") { Detener "Ruta de salida inesperada: $Salida" }
  if (Test-Path -LiteralPath $Salida) {
    Write-Host "Se vacía la salida de la demo: $Salida" -ForegroundColor DarkGray
    Get-ChildItem -LiteralPath $Salida -Force | Remove-Item -Recurse -Force
  }
  Preparar-Salida
  Verificar-Montaje

  $reloj = [System.Diagnostics.Stopwatch]::StartNew()
  $script:Pausas.Reset()
  $psqlConteos = @("exec", "-T", "-u", "postgres", "db", "psql", "-X", "-At", "-d", "olimpiadas", "-f", "/fase2/04_restauracion/conteos.sql")

  Paso 1 "Instancia nueva de PostgreSQL 17 (proyecto $Proyecto)" `
    "el contenedor queda sano, /backups es de postgres y los logs van a 08_demo\salida (archivo centinela visible en /fase2/05_logs)." `
    @( , @("up", "-d", "--wait")
       , @("ps")
       , @("exec", "-T", "-u", "root", "db", "chown", "-R", "postgres:postgres", "/backups")
       , @("exec", "-T", "-u", "postgres", "db", "test", "-f", "/fase2/05_logs/.salida_demo") )

  Paso 2 "Esquema de la Fase 1 y extensiones" `
    "las 11 tablas existen, pgstattuple está instalada y summarize_wal y data_checksums están activos." `
    @( , @("exec", "-T", "-u", "postgres", "db", "psql", "-X", "-q", "-v", "ON_ERROR_STOP=1", "-d", "olimpiadas", "-f", "/fase2/01_ddl/01_esquema.sql")
       , @("exec", "-T", "-u", "postgres", "db", "psql", "-X", "-q", "-v", "ON_ERROR_STOP=1", "-d", "olimpiadas", "-f", "/fase2/01_ddl/02_extensiones.sql")
       , @("exec", "-T", "-u", "postgres", "db", "psql", "-X", "-d", "olimpiadas", "-c", "\dt olimpiadas.*", "-c", "\dx", "-c", "SHOW summarize_wal", "-c", "SHOW data_checksums") )

  Paso 3 "Carga base" `
    "la carga base deja pais 204, poblacion_pais 13026, noc 236, deporte 95, deporte_equivalencia 2 y el resto en 0." `
    @( , @("exec", "-T", "-u", "postgres", "db", "bash", "/fase2/02_carga/cargar_ronda.sh", "deportista", "pc", "base") ) `
    { Verificar-Conteos "base" }

  Paso 4 "Respaldo FULL con pg_basebackup" `
    "el FULL termina, pg_verifybackup lo valida y el CSV de la demo queda con encabezado + 1 fila." `
    @( , @("exec", "-T", "-u", "postgres", "db", "bash", "/fase2/03_backup/backup_full.sh", "deportista", "pc", "demo") ) `
    { Verificar-Lineas 2 }

  $num = 5
  for ($i = 1; $i -le 3; $i++) {
    $ronda = $Rondas[$i - 1]
    $esp = $ConteosEsperados[$ronda]
    Paso $num "Ronda $i ($ronda)" `
      "la ronda se carga en una transacción y los conteos acumulados quedan en sede $($esp[3]), edicion $($esp[4]), evento $($esp[7]), atleta $($esp[8]), participacion $($esp[9]), resultado $($esp[10])." `
      @( , @("exec", "-T", "-u", "postgres", "db", "bash", "/fase2/02_carga/cargar_ronda.sh", "deportista", "pc", $ronda) ) `
      ([scriptblock]::Create("Verificar-Conteos '$ronda'"))
    $num++
    $lineas = 2 + $i
    Paso $num "Respaldo INCR $i encadenado al anterior" `
      "el incremental usa el manifiesto del respaldo anterior, se verifica y el CSV queda con encabezado + $($lineas - 1) filas." `
      @( , @("exec", "-T", "-u", "postgres", "db", "bash", "/fase2/03_backup/backup_incremental.sh", "deportista", "pc", "$i", "demo") ) `
      ([scriptblock]::Create("Verificar-Lineas $lineas"))
    $num++
  }

  Paso $num "Fragmentación antes de borrar la base" `
    "pgstattuple y pgstatindex por tabla e índice; se guarda en CSV para compararla con la fragmentación posterior." `
    @( , @("exec", "-T", "-u", "postgres", "db", "psql", "-X", "-d", "olimpiadas", "-f", "/fase2/04_restauracion/fragmentacion_tablas.sql")
       , @("exec", "-T", "-u", "postgres", "db", "psql", "-X", "-d", "olimpiadas", "-f", "/fase2/04_restauracion/fragmentacion_indices.sql")
       , @("exec", "-T", "-u", "postgres", "db", "bash", "-c", "psql -X -d olimpiadas --csv -f /fase2/04_restauracion/fragmentacion_tablas.sql > /fase2/05_logs/deportista_pc/deportista_pc_09_fragmentacion_tablas.csv")
       , @("exec", "-T", "-u", "postgres", "db", "bash", "-c", "psql -X -d olimpiadas --csv -f /fase2/04_restauracion/fragmentacion_indices.sql > /fase2/05_logs/deportista_pc/deportista_pc_09_fragmentacion_indices.csv") )
  $num++

  Paso $num "Eliminar la base de datos" `
    "DROP DATABASE olimpiadas funciona y la base ya no aparece en la lista." `
    @( , @("exec", "-T", "-u", "postgres", "db", "psql", "-X", "-d", "postgres", "-c", "DROP DATABASE olimpiadas;", "-c", "\l") )
  $num++

  Paso $num "Detener el servicio" `
    "el contenedor db queda en estado Exited; restaurar.sh vacía PGDATA al empezar cada restauración." `
    @( , @("stop", "db")
       , @("ps", "-a") )
  $num++

  # Restauraciones n=0..3, una repetición cada una, sin pausas dentro del bucle.
  $todos = @()
  foreach ($n in 0..3) { $todos += Comandos-Restaurar $n 1 }
  Paso $num "Restaurar las cadenas n=0, 1, 2 y 3 (una repetición cada una)" `
    "cada cadena se combina con pg_combinebackup, pasa pg_verifybackup, arranca y sus conteos son iguales a los del respaldo (diff vacío)." `
    $todos -SinEjecutar {
      foreach ($n in 0..3) {
        foreach ($c in (Comandos-Restaurar $n 1)) {
          Write-Host "> $(Texto-Comando $c)" -ForegroundColor DarkGray
          X $c
        }
        Verificar-Lineas (5 + 4 * ($n + 1))
        Mostrar-Diff $n 1
      }
    }
  $num++

  Paso $num "Fragmentación después de restaurar y comparación final" `
    "la base restaurada (cadena 3) tiene los mismos conteos que al tomar el INCR 3 y la fragmentación es idéntica a la de antes." `
    @( , @("up", "-d", "--wait")
       , $psqlConteos
       , @("exec", "-T", "-u", "postgres", "db", "bash", "-c", "psql -X -At -d olimpiadas -f /fase2/04_restauracion/conteos.sql | diff /backups/conteos_incr3.txt - && echo CONTEOS_IGUALES_AL_INCR3")
       , @("exec", "-T", "-u", "postgres", "db", "psql", "-X", "-d", "olimpiadas", "-f", "/fase2/04_restauracion/fragmentacion_tablas.sql")
       , @("exec", "-T", "-u", "postgres", "db", "psql", "-X", "-d", "olimpiadas", "-f", "/fase2/04_restauracion/fragmentacion_indices.sql")
       , @("exec", "-T", "-u", "postgres", "db", "bash", "-c", "psql -X -d olimpiadas --csv -f /fase2/04_restauracion/fragmentacion_tablas.sql > /fase2/05_logs/deportista_pc/deportista_pc_16_fragmentacion_tablas.csv")
       , @("exec", "-T", "-u", "postgres", "db", "bash", "-c", "psql -X -d olimpiadas --csv -f /fase2/04_restauracion/fragmentacion_indices.sql > /fase2/05_logs/deportista_pc/deportista_pc_16_fragmentacion_indices.csv")
       , @("exec", "-T", "-u", "postgres", "db", "bash", "-c", "cd /fase2/05_logs/deportista_pc && diff deportista_pc_09_fragmentacion_tablas.csv deportista_pc_16_fragmentacion_tablas.csv && diff deportista_pc_09_fragmentacion_indices.csv deportista_pc_16_fragmentacion_indices.csv && echo FRAGMENTACION_IDENTICA") )

  $reloj.Stop()
  Write-Host ""
  Write-Host "Ciclo completo terminado." -ForegroundColor Green
  Write-Host ("Tiempo total: {0:mm\:ss} (sin contar las pausas: {1:mm\:ss})" -f $reloj.Elapsed, ($reloj.Elapsed - $script:Pausas.Elapsed))
  Write-Host "Logs y CSV de la demo en: $Salida"
}

# ---------------------------------------------------------------- opción C

function Opcion-C {
  Confirmar-Proyecto
  $r = Recursos-Demo
  if ($r.Volumenes.Count -eq 0) { Write-Host "No existe el proyecto $Proyecto. Ejecuta antes la opción B." -ForegroundColor Red; return }
  if (-not (Test-Path -LiteralPath $CsvDemo)) { Write-Host "No existe $CsvDemo. Ejecuta antes la opción B." -ForegroundColor Red; return }
  Verificar-Montaje

  $n = Read-Host "Cadena a restaurar, n (0=FULL, 1, 2 o 3)"
  if ($n -notmatch '^[0-3]$') { Write-Host "n debe ser 0, 1, 2 o 3." -ForegroundColor Red; return }
  $rep = Read-Host "Repetición (1 a 3)"
  if ($rep -notmatch '^[1-3]$') { Write-Host "La repetición debe ser 1, 2 o 3." -ForegroundColor Red; return }
  $n = [int]$n; $rep = [int]$rep

  $antes = Lineas-Csv $CsvDemo
  $ref = if ($n -eq 0) { "/backups/conteos_full.txt" } else { "/backups/conteos_incr$n.txt" }
  $cmds = (Comandos-Restaurar $n $rep) + , @("run", "--rm", "--no-deps", "-T", "-u", "postgres", "--entrypoint", "cat", "db", $ref)
  Paso 1 "Restaurar la cadena n=$n, repetición $rep" `
    "la cadena elegida se reconstruye desde PGDATA vacío y sus conteos son iguales a $ref (diff vacío); el CSV gana 4 filas." `
    $cmds `
    ([scriptblock]::Create("Verificar-Lineas $($antes + 4); Mostrar-Diff $n $rep"))
  Write-Host "El servicio db queda detenido con la cadena n=$n en PGDATA." -ForegroundColor DarkGray
}

# ---------------------------------------------------------------- opción D

function Opcion-D {
  Confirmar-Proyecto
  $r = Recursos-Demo
  Write-Host ""
  Write-Host "PASO 1: Limpiar la demo" -ForegroundColor Cyan
  Write-Host "Qué se comprueba: se borran solo el contenedor, la red y los volúmenes de $Proyecto; $ProyectoOfic y olimpiadas_pg no cambian." -ForegroundColor Yellow
  Write-Host "Recursos de ${Proyecto}: $($r.Contenedores.Count) contenedores, $($r.Volumenes.Count) volúmenes."
  docker volume ls --filter "label=com.docker.compose.project=$Proyecto"
  Write-Host "Comando:" -ForegroundColor DarkGray
  Write-Host "  $(Texto-Comando @('down', '-v'))"
  $ok = Read-Host "Escribe SI (en mayúsculas) para borrar el proyecto $Proyecto"
  if ($ok -cne "SI") { Write-Host "Cancelado. No se borró nada." -ForegroundColor Yellow; return }
  X @("down", "-v")
  $r = Recursos-Demo
  Write-Host "Quedan de ${Proyecto}: $($r.Contenedores.Count) contenedores, $($r.Volumenes.Count) volúmenes." -ForegroundColor Green
  Write-Host "Volúmenes de ${ProyectoOfic}:"
  docker volume ls --filter "label=com.docker.compose.project=$ProyectoOfic"
  Write-Host "La carpeta $Salida se conserva; la opción B la vacía al empezar." -ForegroundColor DarkGray
}

# ---------------------------------------------------------------- menú

$encAnterior = [Console]::OutputEncoding
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Push-Location -LiteralPath $Infra
try {
  Confirmar-Proyecto
  while ($true) {
    Write-Host ""
    Write-Host "Demostración Fase 2, carga por deportista (proyecto $Proyecto)" -ForegroundColor Cyan
    Write-Host "  A. Mostrar la evidencia oficial de $ProyectoOfic (solo lectura)"
    Write-Host "  B. Ciclo completo de demostración en $Proyecto"
    Write-Host "  C. Restaurar una cadena concreta en $Proyecto"
    Write-Host "  D. Limpiar la demo (down -v de $Proyecto)"
    Write-Host "  S. Salir"
    $op = Read-Host "Opción"
    if ($null -eq $op) { break }
    switch ($op.Trim().ToUpper()) {
      "A" { Opcion-A }
      "B" { Opcion-B }
      "C" { Opcion-C }
      "D" { Opcion-D }
      "S" { return }
      default { Write-Host "Opción no válida." -ForegroundColor Yellow }
    }
  }
}
finally {
  Pop-Location
  [Console]::OutputEncoding = $encAnterior
}
