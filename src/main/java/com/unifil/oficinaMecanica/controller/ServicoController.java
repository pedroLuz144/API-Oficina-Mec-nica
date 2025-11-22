package com.unifil.oficinaMecanica.controller;

import com.unifil.oficinaMecanica.dto.request.ServicoRequestDTO;
import com.unifil.oficinaMecanica.dto.response.ServicoResponseDTO;
import com.unifil.oficinaMecanica.service.interfaces.ServicoService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/servicos")
@Tag(name = "Serviços", description = "Catálogo de serviços oferecidos pela oficina")
public class ServicoController {

    @Autowired
    private ServicoService servicoService;

    @PostMapping
    @Operation(summary = "Cadastra um novo serviço", description = "Adiciona um serviço ao catálogo com descrição, valor e duração estimada.")
    public ResponseEntity<?> cadastrarServico(@RequestBody @Valid ServicoRequestDTO dto) {
        try {
            servicoService.cadastrarNovoServico(dto);
            return new ResponseEntity<>("Serviço criado com sucesso!", HttpStatus.CREATED);
        } catch (Exception e) {
            return new ResponseEntity<>(e.getMessage(), HttpStatus.BAD_REQUEST);
        }
    }

    @GetMapping
    @Operation(summary = "Lista serviços disponíveis", description = "Retorna o catálogo completo de serviços cadastrados.")
    public ResponseEntity<List<ServicoResponseDTO>> listarServicos() {
        return ResponseEntity.ok(servicoService.getServicos());
    }

    @DeleteMapping("/{id}")
    @Operation(summary = "Remove um serviço", description = "Remove um serviço do catálogo. Cuidado se houver OS usando este serviço.")
    public ResponseEntity<?> removerServico(@PathVariable Long id) {
        try {
            servicoService.removerServico(id);
            return ResponseEntity.noContent().build();
        } catch (Exception e) {
            return new ResponseEntity<>(e.getMessage(), HttpStatus.BAD_REQUEST);
        }
    }
}