from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.exc import OperationalError, IntegrityError
from flask import Flask, render_template, request, redirect, url_for, flash
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sua_chave'
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql://root:123456@localhost/formulario_declaracao"
db = SQLAlchemy(app)

try:
    db.session.execute('SELECT 1')
    print("Conexão com o banco de dados bem-sucedida.")
except Exception as e:
    print(f"Erro ao conectar ao banco de dados: {e}")


class Funcionario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome_completo = db.Column(db.String(100), nullable=False)
    rg = db.Column(db.String(20), nullable=False)
    cpf = db.Column(db.String(20), nullable=False)
    cargo_publico = db.Column(db.String(50), nullable=False)
    endereco_rua = db.Column(db.String(100), nullable=False)
    endereco_cep = db.Column(db.String(20), nullable=False)
    nome_conjuge = db.Column(db.String(100))
    rg_conjuge = db.Column(db.String(20))
    patrimonios = db.relationship('Patrimonio', backref='funcionario', lazy=True)
    conjuges = db.relationship('Conjugue', backref='funcionario', lazy=True, uselist=False)
    dependentes = db.relationship('Dependente', backref='funcionario', lazy=True)
    protocolo = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4())) 

class Patrimonio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(100), nullable=False)
    valor = db.Column(db.Float, nullable=False, default=0.0) # Define 0.0 como padrão
    funcionario_id = db.Column(db.Integer, db.ForeignKey('funcionario.id'), nullable=False)

class Conjugue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    rg = db.Column(db.String(20))
    funcionario_id = db.Column(db.Integer, db.ForeignKey('funcionario.id'), nullable=False)
    patrimonios = db.relationship('PtrConjugue', backref='conjugue', lazy=True)

class PtrConjugue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(100), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    id_ptr_conjugue = db.Column(db.Integer, db.ForeignKey('conjugue.id'), nullable=False)

class Dependente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    rg = db.Column(db.String(20))
    funcionario_id = db.Column(db.Integer, db.ForeignKey('funcionario.id'), nullable=False)
    patrimonios = db.relationship('PtrDependente', backref='dependente', lazy=True)

class PtrDependente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(100), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    id_ptr_dependente = db.Column(db.Integer, db.ForeignKey('dependente.id'), nullable=False)
    
@app.route("/")
def index():
    funcionarios = Funcionario.query.all()
    return render_template("Index/index.html", funcionarios=funcionarios)

@app.route("/create", methods=["GET", "POST"])
def create():
    if request.method == "POST":
        # Validação dos campos obrigatórios
        if not all([
            request.form["nome_completo"],
            request.form["rg"],
            request.form["cpf"],
            request.form["cargo_publico"],
            request.form["endereco_rua"],
            request.form["endereco_cep"],
        ]):
            flash('Por favor, preencha todos os campos obrigatórios.', 'error')
            return render_template("Create/create.html")

        try:
            funcionario = Funcionario(
                nome_completo=request.form["nome_completo"],
                rg=request.form["rg"],
                cpf=request.form["cpf"],
                cargo_publico=request.form["cargo_publico"],
                endereco_rua=request.form["endereco_rua"],
                endereco_cep=request.form["endereco_cep"],
            )

            protocolo_uuid = uuid.uuid4()
            protocolo_base64 = protocolo_uuid.bytes.hex() 
            funcionario.protocolo = protocolo_base64 
            
            db.session.add(funcionario)
            db.session.flush()  # Faz o banco de dados gerar o ID do funcionário

            # Cônjuge
            if request.form.get("possui_conjuge") == 'sim':
                # Validação dos campos do cônjuge
                if not all([
                    request.form["nome_conjuge"],
                    request.form["rg_conjuge"],
                ]):
                    flash('Por favor, preencha todos os campos do cônjuge.', 'error')
                    return render_template("Create/create.html")

                funcionario.nome_conjuge = request.form["nome_conjuge"]
                funcionario.rg_conjuge = request.form["rg_conjuge"]

                conjugue = Conjugue(
                    nome=request.form["nome_conjuge"],
                    rg=request.form["rg_conjuge"],
                    funcionario_id=funcionario.id
                )
                db.session.add(conjugue) 
                db.session.flush() # Garante que o cônjuge tenha um ID
                
                # Patrimônios do Cônjuge - AGORA com o ID do cônjuge
                for i in range(len(request.form.getlist("descricao_patrimonio_conjuge[]"))):
                    descricao = request.form.getlist("descricao_patrimonio_conjuge[]")[i]
                    valor = request.form.getlist("valor_patrimonio_conjuge[]")[i]
                    try:
                        valor = int(valor)
                    except ValueError:
                        flash('Valor do patrimônio do cônjuge inválido. Por favor, insira um número válido.', 'error')
                        return render_template("Create/create.html")

                    conjugue_patrimonio = PtrConjugue(
                        descricao=descricao,
                        valor=valor,
                        id_ptr_conjugue=conjugue.id  
                    )
                    db.session.add(conjugue_patrimonio)

            # Dependente
            if request.form.get("possui_dependente") == 'sim':
                # Validação dos campos do dependente
                if not all([
                    request.form["nome_dependente"],
                    request.form["rg_dependente"],
                ]):
                    flash('Por favor, preencha todos os campos do dependente.', 'error')
                    return render_template("Create/create.html")

                dependente = Dependente(
                    nome=request.form["nome_dependente"],
                    rg=request.form["rg_dependente"],
                    funcionario_id=funcionario.id
                )
                db.session.add(dependente)
                db.session.flush()  # Garante que o dependente tenha um ID
                
                 # Patrimônios do Dependente - AGORA com o ID do dependente
                for i in range(len(request.form.getlist("descricao_patrimonio_dependente[]"))):
                    descricao = request.form.getlist("descricao_patrimonio_dependente[]")[i]
                    valor = request.form.getlist("valor_patrimonio_dependente[]")[i]
                    try:
                        valor = int(valor)
                    except ValueError:
                        flash('Valor do patrimônio do dependente inválido. Por favor, insira um número válido.', 'error')
                        return render_template("Create/create.html")

                    dependente_patrimonio = PtrDependente(
                        descricao=descricao,
                        valor=valor,
                        id_ptr_dependente=dependente.id  
                    )
                    db.session.add(dependente_patrimonio)

            # Salvando os patrimônios associados ao funcionário
            for i in range(len(request.form.getlist("descricao_patrimonio[]"))):
                descricao = request.form.getlist("descricao_patrimonio[]")[i]
                valor = request.form.getlist("valor_patrimonio[]")[i]
                try:
                    valor = int(valor)
                except ValueError:
                    flash('Valor do patrimônio inválido. Por favor, insira um número válido.', 'error')
                    return render_template("Create/create.html")

                patrimonio = Patrimonio(descricao=descricao, valor=valor, funcionario_id=funcionario.id)
                db.session.add(patrimonio)

            db.session.commit()
            flash('Declaração de bens registrada com sucesso!', 'success')
            return redirect(url_for("show_funcionario", funcionario_id=funcionario.id))
        
        except (OperationalError, IntegrityError) as e:
            db.session.rollback()
            flash(f'Erro ao registrar declaração: {str(e)}', 'error')
            return render_template("Create/create.html")
    return render_template("Create/create.html")

@app.route("/update/<int:id>", methods=["GET", "POST"])
def update(id):
    funcionario = Funcionario.query.get(id)
    if request.method == "POST":
        funcionario.nome_completo = request.form["nome_completo"]
        funcionario.rg = request.form["rg"]
        funcionario.cpf = request.form["cpf"]
        funcionario.cargo_publico = request.form["cargo_publico"]
        funcionario.endereco_rua = request.form["endereco_rua"]
        funcionario.endereco_cep = request.form["endereco_cep"]
        
        if request.form.get("nome_conjuge"):
            if not funcionario.conjuges:
                conjugue = Conjugue(
                    nome=request.form["nome_conjuge"],
                    rg=request.form["rg_conjuge"],
                    funcionario_id=funcionario.id
                )
                db.session.add(conjugue)
            else:
                conjugue = funcionario.conjuges
                conjugue.nome = request.form["nome_conjuge"]
                conjugue.rg = request.form["rg_conjuge"]
        
        if request.form.get("nome_dependente"):
            if not funcionario.dependentes:
                dependente = Dependente(
                    nome=request.form["nome_dependente"],
                    rg=request.form["rg_dependente"],
                    funcionario_id=funcionario.id
                )
                db.session.add(dependente)
            else:
                dependente = funcionario.dependentes[0]  # Assuming one dependente for simplicity
                dependente.nome = request.form["nome_dependente"]
                dependente.rg = request.form["rg_dependente"]
                
        db.session.commit()
        return redirect(url_for("index"))
    return render_template("Update/update.html", funcionario=funcionario)


@app.route("/delete/<int:id>")
def delete(id):
    funcionario = Funcionario.query.get(id)
    db.session.delete(funcionario)
    db.session.commit()
    return redirect(url_for("index"))

@app.route("/nao_possui_bens", methods=["GET", "POST"])
def nao_possui_bens():
    if request.method == "POST":
        funcionario = Funcionario(
            nome_completo=request.form["nome_completo"],
            rg=request.form["rg"],
            cpf=request.form["cpf"],
            cargo_publico=request.form["cargo_publico"],
            endereco_rua=request.form["endereco_rua"],
            endereco_cep=request.form["endereco_cep"]
        )
        db.session.add(funcionario)
        db.session.commit()  # Confirma a adição do funcionário
        
        # Obtem o ID do funcionário recém-criado
        funcionario_id = funcionario.id 
        
        return redirect(url_for("show_funcionario", funcionario_id=funcionario_id)) 
    else:  
        return render_template("NaoPossui/nao_possui_bens.html")

@app.route("/funcionario/<int:funcionario_id>")
def show_funcionario(funcionario_id):
    funcionario = Funcionario.query.get_or_404(funcionario_id)
    return render_template("Show/show_funcionario.html", funcionario=funcionario)


if __name__ == "__main__":
    app.run(debug=True)
