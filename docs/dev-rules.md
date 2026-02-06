<Table>
  <tr>
    <td><a href= "link"><img src="img/logo.png" alt="Nome" border="0"></td>
    <td>
      <a href= "https://www.inteli.edu.br/"><img src="img/logo-Inteli.png" alt="Inteli - Instituto de Tecnologia e Liderança" border="0"></a>
    </td>
  </tr>
</table>

# Nome do Projeto: <nome do projeto>

## Nome do Grupo: <nome do grupo>

## Integrantes:

- <a href="https://www.linkedin.com/in/username/">Nome</a>
- <a href="https://www.linkedin.com/in/username/">Nome</a>
- <a href="https://www.linkedin.com/in/username/">Nome</a>
- <a href="https://www.linkedin.com/in/username/">Nome</a>
- <a href="https://www.linkedin.com/in/username/">Nome</a>
- <a href="https://www.linkedin.com/in/username/">Nome</a>
- <a href="https://www.linkedin.com/in/username/">Nome</a>
- <a href="https://www.linkedin.com/in/username/">Nome</a>

# Sumário



# 1. Introdução
_conteúdo_

## 1.1 Objetivo do Documento

Este documento apresenta estabelecer padrões de codificação e práticas de desenvolvimento para garantir a qualidade e a consistência do código.

Nota: Explicar a importância de seguir padrões de desenvolvimento para facilitar a manutenção, melhorar a legibilidade e promover a colaboração.

# 2. Padrões de Codificação
_conteúdo_

## 2.1 Naming Conventions

- Variáveis e Funções: Utilize camelCase
  - Exemplos:
    - ```let userName = "John";``` 
    - ```function calculateTotal() { ... } 

- Classes e Interfaces: Utilize PascalCase
  - Exemplos:
    - ```class UserProfile { ... }``` 
    - ```interface PaymentGateway { ... }```  

- Constantes: Utilize UPPER_CASE com underscores
  - Exemplo:
    - const MAX_USERS = 100; 

## 2.2 Formatação de Código

- Indentação: Utilize 2 espaços para indentação.
- Linhas: Mantenha o comprimento das linhas em até 80 caracteres.
- Chaves: Coloque chaves de abertura na mesma linha.
  - Exemplo:
    ```
    if (condition) {
        // código
    }
    ```

## 2.3 Comentários e Documentação

- Comentários de Linha: Use para explicar lógica complexa.
  - Exemplo: // Calcula o total com desconto

- Comentários de Bloco: Use para documentar funções e classes com JSDoc.
  - Exemplo: 
    ```
    /**
    * Calcula o total de um pedido.
    * @param {number} price - Preço do item.
    * @param {number} quantity - Quantidade do item.
    * @returns {number} Total calculado.
    */
    function calculateTotal(price, quantity) {
        return price * quantity;
    }
    ```

- Documentação da API
  - Utilizar SWAGGER para documentação da API a partir dos comentários do código.
  - Configure uma rota, como /api-docs, para que a documentação gerada pelo Swagger seja facilmente acessível aos desenvolvedores e stakeholders.

# 3. Padrões de Projeto
_conteúdo_

## 3.1 Design Patterns

_Opcionalmente, o grupo pode definir um ou mais design patterns para serem adotados, como forma de exercitarem tipos de solução para problemas/situações recorrentes_
_Sugestão de leitura: https://refactoring.guru/_

## 3.2 Arquitetura de Software

- Utilize a Arquitetura de Três Camadas: Separe a lógica de negócios (Camada de Negócios), a interface do usuário (Camada de Apresentção) e o acesso aos dados (Camada de Dados).
  - Exemplo: Em uma aplicação Angular, utilize serviços para lógica de negócios, componentes para a interface e controladores para gerenciar a interação.

# 4. Práticas de Desenvolvimento
_conteúdo_

## 4.1 Testes Automatizados

- Testes Unitários: Utilize Jest para criar testes unitários
  - Exemplo:
    ```
    test('adiciona 1 + 2 para igualar 3', () => {
      expect(1 + 2).toBe(3);
    });
    ```

- Testes de Integração: Como sugestão, utilizar o Cypress para testes de integração.
  - Exemplo: Testar a interação entre componentes de frontend e backend.

- Testes end-to-end: Como sugestão, utilizar o Cypress para testes end-to-end. 
  - Exemplo: Testar um RF de ponta a ponta.

## 4.2 Controle de Qualidade

- Revisão de Código: Todos os commits devem ser revisados por pelo menos um outro desenvolvedor.

- Sugestão: Utilizar ESLint para análise estática de código JavaScript/TypeScript.

# 5. Ferramentas e Tecnologias

## 5.1 Ferramentas de Desenvolvimento

- Editor de Código: Utilize Visual Studio Code como editor padrão.

- Plugins recomendados: ESLint, Prettier, GitLens.

## 5.2 Tecnologias e Frameworks
