<Table>
  <tr>
    <td><a href= "https://www.sankhya.com.br/software-de-gestao-erp/erp-para-gestao-empresarial/produtos/asis/"><img src="docs/img/asis.png" alt="Asis" border="0"></td>
    <td>
      <a href= "https://www.inteli.edu.br/"><img src="docs/img/logo-Inteli.png" alt="Inteli - Instituto de Tecnologia e Liderança" border="0"></a>
    </td>
  </tr>
</table>

# Nome do Projeto: P.G.S (Projeto do Grupo Seis)

## Nome do Grupo: O.G.S (O Grupo Seis)

## Integrantes:

- <a href="https://www.linkedin.com/in/arthur-bretas/">Arthur Bretas Oliveira</a>
- <a href="https://www.linkedin.com/in/daviversan/">Davi D'avila Versan</a>
- <a href="https://www.linkedin.com/in/gabriel-nascimento3/">Gabriel Santos do Nascimento</a>
- <a href="https://www.linkedin.com/in/nicolasramons/">Nicolas Ramon da Silva</a>
- <a href="https://www.linkedin.com/in/otavio-vasc/">Otavio de Carvalho Vasconcelos</a>
- <a href="https://www.linkedin.com/in/vitor-balbo/">Vitor Margarido Balbo</a>
- <a href="https://www.linkedin.com/in/viniciussavian/">Vinicius dos Reis Savian</a>


## Professores:
### Orientador(a) 
- <a href="https://www.linkedin.com/in/reginaldo-arakaki-9574222b/">Reginaldo Arakaki</a>
### Instrutores
- <a href="https://www.linkedin.com/in/reginaldo-arakaki-9574222b/">Computação - Reginaldo</a>
- <a href="https://www.linkedin.com/in/ovidio-netto/">Computação - Ovídio</a>
- <a href="https://www.linkedin.com/in/fernando-pizzo-208b526a/">Matemática e Física - Pizzo</a>
- <a href="https://www.linkedin.com/in/pedroteberga/">Negócios - Pedro</a>
- <a href="https://www.linkedin.com/in/gui-cestari/">Design - Cestari</a> 
- <a href="https://www.linkedin.com/in/filipe-gon%C3%A7alves-08a55015b/">Liderança - Filipe Gonçalves</a>

## 📝 Descrição

Em um contexto **API First** na ASIS TaxTech, o desafio deste projeto é tratar **qualidade e resiliência como ativo de software**, garantindo que o comportamento da API permaneça correto e estável sob diferentes condições. Para isso, estruturamos uma base de **testes automatizados orientados a dados (TDD/Test Data Driven)**, com critérios objetivos (ex.: latência, integridade de payload, disponibilidade, não-repúdio) e evidências reproduzíveis, além de insumos para análises de qualidade/arquitetura/segurança e evolução para execução em **esteira de CI/CD**.

## 📝 LINKS

<a href="/docs/index.md">Link para a documentação geral</a> do projeto.

## 📁 Estrutura de pastas

```
g06/
├─ docs/
│  ├─ index.md
│  ├─ projeto.md
│  ├─ gestao-projeto.md
│  ├─ gestao-configuração.md
│  └─ dev-rules.md
├─ img/
├─ src/
│  ├─ core/
│  │  ├─ mock_api.py
│  │  ├─ availability.py
│  │  └─ non_repudiation.py
│  └─ tests/
│     ├─ blue_team/
│     └─ red_team/
├─ requirements.txt
├─ Makefile
└─ README.md
```


Dentre os arquivos presentes na raiz do projeto, definem-se:

- <b>readme.md</b>: arquivo que serve como guia e explicação geral sobre o projeto (o mesmo que você está lendo agora).

- <b>documentos</b>: aqui estarão todos os documentos do projeto. Há também uma pasta denominada <b>outros</b> onde podem estar presentes documentos complementares à documentação principal.

- <b>imagens</b>: imagens relacionadas ao projeto como um todo (por exemplo imagens do sistema, do grupo, logotipos e afins).

- <b>src</b>: nesta pasta encontra-se todo o código fonte do sistema (circuito e eventuais sistemas complementares).

## 💻 Configuração para desenvolvimento

Para configurar o desenvolvimento da aplicação, [instale o git](https://git-scm.com/downloads) e clone esse repositório em seu computador através do comando:

```
git clone https://git.inteli.edu.br/graduacao/2026-1a/t13/g06
```
Em seguida siga as instruções presentes em nosso <a href="/documentos/manual-instalacao.md">manual de instalação</a>.

## 🗃 Histórico de lançamentos

* 0.1.0 - 13/02/2026
    * ESPECIFICAÇÃO DOS BUSINESS DRIVERS (Documento de Negócio como Ativo de Software)
* 0.2.0 - 27/02/2026
    * REQUISITOS FUNCIONAIS E NÃO FUNCIONAIS COMO CÓDIGO
* 0.3.0 - 13/03/2026
    * ESPECIFICAÇÃO DA SOLUÇÃO TÉCNICA COMO CÓDIGO
* 0.4.0 - 27/03/2026
    * DASHBOARD DE CÓDIGOS DE QUALIDADE (Negócio, Requisitos, Soluções e demais estatísticas)
* 0.5.0 - 10/04/2026
    * PROJETO FINALIZADO STORYTELLING DO PROJETO REPOSITÓRIO ORGANIZADO


## 📋 Licença/License

<p xmlns:cc="http://creativecommons.org/ns#" xmlns:dct="http://purl.org/dc/terms/"><a property="dct:title" rel="cc:attributionURL" href="https://git.inteli.edu.br/graduacao/2026-1a/t13/g06">P.G.S (Projeto do Grupo Seis)</a> by <a rel="cc:attributionURL dct:creator" property="cc:attributionName" href="https://git.inteli.edu.br/graduacao/2026-1a/t13/g06">INTELI, Arthur Bretas Oliveira, Davi D'avila Versan, Gabriel Santos do Nascimento, Nicolas Ramon da Silva, Otavio de Carvalho Vasconcelos, Vitor Margarido Balbo, Vinicius dos Reis Savian</a> is licensed under <a href="http://creativecommons.org/licenses/by/4.0/?ref=chooser-v1" target="_blank" rel="license noopener noreferrer" style="display:inline-block;">Attribution 4.0 International<img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/cc.svg?ref=chooser-v1"><img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/by.svg?ref=chooser-v1"></a></p>