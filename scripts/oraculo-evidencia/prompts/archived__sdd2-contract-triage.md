# Lectura independiente de un flujo de trabajo

Vas a leer tres documentos de un mismo flujo de trabajo y a responder una sola pregunta sobre cada
una de sus tareas. Sos un lector, no un revisor: no evalúes si el flujo está bien hecho.

## Los documentos

- especificación: `.plans/archived/sdd2-contract-triage/spec.md`
- plan: `.plans/archived/sdd2-contract-triage/plan.md`
- tareas: `.plans/archived/sdd2-contract-triage/tasks.md`

Leelos enteros antes de responder. **No abras ningún otro archivo del repositorio**, ni busques
contexto fuera de esos tres.

## La pregunta

Para **cada tarea** del documento de tareas: ¿de qué criterios de aceptación de la especificación
dice esa tarea, ella misma, que se hace cargo?

Responde por lo que la tarea dice de sí misma. No completes con lo que te parezca que debería
cubrir ni con lo que deducís de lo que hace.

## Cómo responder

Un objeto JSON y nada más — sin texto alrededor, sin cercas de código:

```
{
  "flujo": "archived/sdd2-contract-triage",
  "tareas": [
    {
      "tarea": "<el identificador de la tarea, tal como aparece en el documento>",
      "criterios": ["<identificador de criterio>", "..."],
      "cita": "<el texto literal del documento donde la tarea lo dice>"
    }
  ]
}
```

- **Una entrada por tarea**, en el orden en que aparecen, incluidas las que no se hacen cargo de
  ninguno: ahí `criterios` va vacío y `cita` también.
- Si la misma tarea aparece más de una vez, poné una entrada por aparición, en orden.
- La `cita` se **copia literal**, sin reescribir ni recortar a la mitad de una palabra. Sin ella no
  hay forma de distinguir lo que leíste de lo que inferiste.
- Los identificadores se copian tal como están escritos, con sus mayúsculas y sus sufijos.
