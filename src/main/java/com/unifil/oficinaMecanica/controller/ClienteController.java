package com.unifil.oficinaMecanica.controller;

import com.unifil.oficinaMecanica.dto.request.ClienteRequestDTO;
import com.unifil.oficinaMecanica.dto.response.VeiculoResponseDTO;
import com.unifil.oficinaMecanica.service.interfaces.ClienteService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/clientes")
@Tag(name = "Clientes", description = "Endpoints para gerenciamento de clientes")
public class ClienteController {

    @Autowired
    private ClienteService clienteService;

    @PostMapping
    @Operation(summary = "Cadastra um novo cliente", description = "Requer CPF, nome e email válidos.")
    public ResponseEntity<?> cadastrarCliente(@RequestBody @Valid ClienteRequestDTO dto) {
        try {
            clienteService.cadastrarNovoCliente(dto);
            return new ResponseEntity<>("Cliente cadastrado com sucesso!", HttpStatus.CREATED);
        } catch (Exception e) {
            return new ResponseEntity<>(e.getMessage(), HttpStatus.BAD_REQUEST);
        }
    }

    @PutMapping("/{cpf}")
    @Operation(summary = "Atualiza as informações do cliente", description = "Só não é possível atualizar o CPF, mas o mesmo deve ser passado como um pathVariable.")
    public ResponseEntity<?> atualizarCliente(@PathVariable String cpf, @RequestBody @Valid ClienteRequestDTO dto) {
        try {
            if (!cpf.equals(dto.cpf())) {
                return new ResponseEntity<>("O CPF da URL difere do CPF do corpo da requisição.", HttpStatus.BAD_REQUEST);
            }
            clienteService.atualizarInformacoes(dto);
            return ResponseEntity.ok("Cliente atualizado com sucesso.");
        } catch (Exception e) {
            return new ResponseEntity<>(e.getMessage(), HttpStatus.BAD_REQUEST);
        }
    }

    @DeleteMapping("/{cpf}")
    @Operation(summary = "Remove um cliente", description = "Só não é possível remover um cliente que ainda tem um carro cadastrado e ou uma OS cadastrada no carro.")
    public ResponseEntity<?> removerCliente(@PathVariable String cpf) {
        try {
            clienteService.removerCliente(cpf);
            return ResponseEntity.noContent().build();
        } catch (Exception e) {
            return new ResponseEntity<>(e.getMessage(), HttpStatus.BAD_REQUEST);
        }
    }

    @GetMapping("/{cpf}/veiculos")
    @Operation(summary = "Lista todos os veículos do cliente", description = "Precisa de um CPF de um cliente cadastrado para buscar os carros.")
    public ResponseEntity<List<VeiculoResponseDTO>> listarVeiculosDoCliente(@PathVariable String cpf) {
        List<VeiculoResponseDTO> veiculos = clienteService.getVeiculos(cpf);
        return ResponseEntity.ok(veiculos);
    }
}