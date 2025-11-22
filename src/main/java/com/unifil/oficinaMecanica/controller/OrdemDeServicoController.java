package com.unifil.oficinaMecanica.controller;

import com.unifil.oficinaMecanica.dto.request.OrdemDeServicoRequestDTO;
import com.unifil.oficinaMecanica.dto.response.OrdemDeServicoResponseDTO;
import com.unifil.oficinaMecanica.service.interfaces.OrdemDeServicoService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/os")
@Tag(name = "Ordem de Serviço", description = "Gerenciamento de abertura, fluxo e finalização das OS")
public class OrdemDeServicoController {

    @Autowired
    private OrdemDeServicoService ordemDeServicoService;

    @PostMapping
    @Operation(summary = "Abre uma nova OS", description = "Cria uma OS com status 'EM_ABERTO', vinculando um veículo a um serviço.")
    public ResponseEntity<?> abrirNovaOS(@RequestBody @Valid OrdemDeServicoRequestDTO dto) {
        try {
            ordemDeServicoService.cadastrarNovaOrdemDeServico(dto);
            return new ResponseEntity<>("Ordem de Serviço aberta com sucesso!", HttpStatus.CREATED);
        } catch (Exception e) {
            return new ResponseEntity<>(e.getMessage(), HttpStatus.BAD_REQUEST);
        }
    }

    @GetMapping("/abertas")
    @Operation(summary = "Lista OS não finalizadas", description = "Retorna todas as ordens de serviço que estão 'EM_ABERTO' ou 'EM_ANDAMENTO'.")
    public ResponseEntity<List<OrdemDeServicoResponseDTO>> listarOSEmAberto() {
        return ResponseEntity.ok(ordemDeServicoService.getOrdemDeServicosEmAberto());
    }

    @PatchMapping("/{id}/status")
    @Operation(summary = "Atualiza o status da OS", description = "Permite transitar o status (ex: de 'EM_ABERTO' para 'EM_ANDAMENTO').")
    public ResponseEntity<?> atualizarStatus(@PathVariable Long id, @RequestParam String novoStatus) {
        try {
            ordemDeServicoService.atualizarStatusDaOrdemDeServico(id, novoStatus);
            return ResponseEntity.ok("Status atualizado com sucesso.");
        } catch (Exception e) {
            return new ResponseEntity<>(e.getMessage(), HttpStatus.BAD_REQUEST);
        }
    }

    @PatchMapping("/{id}/finalizar")
    @Operation(summary = "Finaliza uma OS", description = "Define o status da OS como 'FINALIZADA' e encerra o fluxo de serviço.")
    public ResponseEntity<?> finalizarOS(@PathVariable Long id) {
        try {
            ordemDeServicoService.finalizarOrdemDeServico(id);
            return ResponseEntity.ok("Ordem de Serviço finalizada com sucesso.");
        } catch (Exception e) {
            return new ResponseEntity<>(e.getMessage(), HttpStatus.BAD_REQUEST);
        }
    }

    @DeleteMapping("/{id}")
    @Operation(summary = "Remove uma OS", description = "Exclui permanentemente o registro de uma ordem de serviço do banco de dados.")
    public ResponseEntity<?> removerOS(@PathVariable Long id) {
        try {
            ordemDeServicoService.removerOrdemDeServico(id);
            return ResponseEntity.noContent().build();
        } catch (Exception e) {
            return new ResponseEntity<>(e.getMessage(), HttpStatus.BAD_REQUEST);
        }
    }
}