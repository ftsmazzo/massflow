# CORS no Easypanel (MassFlow)

## Backend – variável CORS_ORIGINS

Use **só a URL do frontend** (uma origem), igual à que aparece no navegador.

| Onde | Variável | Valor (exemplo) |
|------|----------|------------------|
| **Backend** | `CORS_ORIGINS` | `https://fabricaia-massflow-frontend.iei9vc.easypanel.host` |

### Formato correto

- Uma única URL.
- Sem barra no final.
- Sem `https://` duplicado (erro comum: `https://https://...`).
- Sem espaços antes/depois.

### No Easypanel

1. Serviço **massflow-backend** → Variáveis de ambiente.
2. Defina **CORS_ORIGINS** = `https://fabricaia-massflow-frontend.iei9vc.easypanel.host`  
   (troque pelo domínio real do seu frontend, se for outro).
3. **CORS_ORIGIN_REGEX** pode ficar vazio ou ser removido.
4. Salve e faça redeploy do backend.

### Se tiver mais de um frontend

Separe por vírgula, sem espaços:

```env
CORS_ORIGINS=https://front1.easypanel.host,https://front2.easypanel.host
```

Em geral em produção usa-se **só um** (a URL do frontend do MassFlow).
