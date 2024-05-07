CREATE TABLE pessoas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome_completo VARCHAR(100) NOT NULL,
    rg VARCHAR(20) NOT NULL,
    cpf VARCHAR(20) NOT NULL,
    cargo_publico VARCHAR(50) NOT NULL,
    endereco_rua VARCHAR(100) NOT NULL,
    endereco_cep VARCHAR(20) NOT NULL
);
