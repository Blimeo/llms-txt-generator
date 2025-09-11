CREATE TABLE projects (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
url TEXT NOT NULL,
config JSONB NOT NULL,
created_at TIMESTAMP DEFAULT now(),
updated_at TIMESTAMP DEFAULT now()
);


CREATE TABLE runs (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
project_id UUID REFERENCES projects(id),
status TEXT,
llms_txt TEXT,
created_at TIMESTAMP DEFAULT now()
);