CREATE TABLE respostas_claude (
  id BIGSERIAL PRIMARY KEY,
  conteudo TEXT NOT NULL,
  lida BOOLEAN DEFAULT FALSE,
  criado_em TIMESTAMPTZ DEFAULT NOW()
);
GRANT ALL ON public.respostas_claude TO service_role;
GRANT ALL ON public.respostas_claude_id_seq TO service_role;
