package com.unifil.oficinaMecanica.controller;

import com.unifil.oficinaMecanica.dto.request.VeiculoRequestDTO;
import com.unifil.oficinaMecanica.dto.response.VeiculoResponseDTO;
import com.unifil.oficinaMecanica.service.interfaces.VeiculoService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/veiculos")
@Tag(name = "Veículos", description = "Endpoints para gerenciamento dos veículos dos clientes")
public class VeiculoController {

    @Autowired
    private VeiculoService veiculoService;

    @PostMapping
    @Operation(summary = "Cadastra um novo veículo", description = "Registra um veículo e o associa a um cliente existente via CPF.")
    public ResponseEntity<?> cadastrarVeiculo(@RequestBody @Valid VeiculoRequestDTO dto) {
        try {
            veiculoService.cadastrarNovoVeiculo(dto);
            return new ResponseEntity<>("Veículo cadastrado com sucesso!", HttpStatus.CREATED);
        } catch (Exception e) {
            return new ResponseEntity<>(e.getMessage(), HttpStatus.BAD_REQUEST);
        }
    }

    @GetMapping
    @Operation(summary = "Cadastra um novo veículo", description = "Registra um veículo e o associa a um cliente existente via CPF.")
    public ResponseEntity<List<VeiculoResponseDTO>> listarVeiculos() {
        List<VeiculoResponseDTO> veiculos = veiculoService.listarVeiculos();
        return ResponseEntity.ok(veiculos);
    }

    @GetMapping("/{placa}")
    @Operation(summary = "Busca veículo por placa", description = "Retorna os detalhes de um veículo específico baseado na placa informada.")
    public ResponseEntity<?> buscarVeiculoPorPlaca(@PathVariable String placa) {
        VeiculoResponseDTO veiculo = veiculoService.buscarVeiculoPelaPlaca(placa);

        if (veiculo != null) {
            return ResponseEntity.ok(veiculo);
        } else {
            return new ResponseEntity<>("Veículo não encontrado.", HttpStatus.NOT_FOUND);
        }
    }

    @PutMapping("/{placa}")
    @Operation(summary = "Atualiza dados do veículo", description = "Atualiza marca, modelo e cor de um veículo existente. A placa não pode ser alterada.")
    public ResponseEntity<?> atualizarVeiculo(@PathVariable String placa, @RequestBody @Valid VeiculoRequestDTO dto) {
        try {
            veiculoService.atualizarInformacoes(placa, dto);
            return ResponseEntity.ok("Veículo atualizado com sucesso.");
        } catch (Exception e) {
            return new ResponseEntity<>(e.getMessage(), HttpStatus.BAD_REQUEST);
        }
    }

    @DeleteMapping("/{placa}")
    @Operation(summary = "Remove um veículo", description = "Exclui um veículo do sistema. Falhará se houver ordens de serviço vinculadas a ele.")
    public ResponseEntity<?> removerVeiculo(@PathVariable String placa) {
        try {
            veiculoService.removerVeiculoPelaPlaca(placa);
            return ResponseEntity.noContent().build();
        } catch (Exception e) {
            return new ResponseEntity<>(e.getMessage(), HttpStatus.BAD_REQUEST);
        }
    }
}