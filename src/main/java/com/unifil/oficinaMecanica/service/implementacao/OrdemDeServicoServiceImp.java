package com.unifil.oficinaMecanica.service.implementacao;

import com.unifil.oficinaMecanica.async.OrdemStatusAlteradoEvent;
import com.unifil.oficinaMecanica.dto.request.OrdemDeServicoRequestDTO;
import com.unifil.oficinaMecanica.dto.response.OrdemDeServicoResponseDTO;
import com.unifil.oficinaMecanica.entity.OrdemDeServicoEntity;
import com.unifil.oficinaMecanica.entity.ServicoEntity;
import com.unifil.oficinaMecanica.entity.VeiculoEntity;
import com.unifil.oficinaMecanica.repository.OrdemDeServicoRepository;
import com.unifil.oficinaMecanica.repository.ServicoRepository;
import com.unifil.oficinaMecanica.repository.VeiculoRepository;
import com.unifil.oficinaMecanica.service.interfaces.OrdemDeServicoService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Optional;
import java.util.stream.Collectors;

@Service
public class OrdemDeServicoServiceImp implements OrdemDeServicoService {
    @Autowired
    private OrdemDeServicoRepository ordemDeServicoRepository;

    @Autowired
    private VeiculoRepository veiculoRepository;

    @Autowired
    private ServicoRepository servicoRepository;

    @Autowired
    private ApplicationEventPublisher eventPublisher;

    @Override
    public boolean cadastrarNovaOrdemDeServico(OrdemDeServicoRequestDTO dto) throws Exception {
        try {
            Optional<VeiculoEntity> veiculoOptional = veiculoRepository.findById(dto.placaVeiculo());
            Optional<ServicoEntity> servicoOptional = servicoRepository.findById(dto.idServico());

            if (veiculoOptional.isEmpty()) {
                throw new Exception("Veículo não encontrado com a placa: " + dto.placaVeiculo());
            }
            if (servicoOptional.isEmpty()) {
                throw new Exception("Serviço não encontrado com o ID: " + dto.idServico());
            }

            OrdemDeServicoEntity ordemDeServico = new OrdemDeServicoEntity();
            ordemDeServico.setVeiculo(veiculoOptional.get());
            ordemDeServico.setServico(servicoOptional.get());

            ordemDeServico.setStatus(OrdemDeServicoEntity.Status.EM_ABERTO);

            ordemDeServicoRepository.save(ordemDeServico);
            return true;
        } catch (Exception e) {
            throw new Exception("Ocorreu um erro ao tentar cadastrar a ordem de serviço.\n" + e.getMessage());
        }
    }

    @Override
    public List<OrdemDeServicoResponseDTO> getOrdemDeServicosEmAberto() {
        List<OrdemDeServicoEntity> osEmAberto = ordemDeServicoRepository.findByStatusNot(OrdemDeServicoEntity.Status.FINALIZADA);

        return osEmAberto.stream()
                .map(os -> {
                    String placa = os.getVeiculo().getPlaca();
                    String marca = os.getVeiculo().getMarca();
                    String servicoDescricao = os.getServico().getDescricao();
                    java.math.BigDecimal servicoValor = os.getServico().getValor();

                    return new OrdemDeServicoResponseDTO(
                            os.getId(),
                            os.getStatus().name(),
                            placa,
                            marca,
                            servicoDescricao,
                            servicoValor
                    );
                })
                .collect(Collectors.toList());
    }

    @Override
    public boolean atualizarStatusDaOrdemDeServico(Long id, String novoStatus) throws Exception {
        Optional<OrdemDeServicoEntity> osOptional = ordemDeServicoRepository.findById(id);

        if (osOptional.isEmpty()) {
            throw new Exception("Ordem de Serviço não encontrada com o ID: " + id);
        }

        OrdemDeServicoEntity ordemDeServico = osOptional.get();

        try {
            OrdemDeServicoEntity.Status statusAnterior = ordemDeServico.getStatus();
            OrdemDeServicoEntity.Status statusConvertido = OrdemDeServicoEntity.Status.valueOf(novoStatus.toUpperCase());

            if (statusAnterior == statusConvertido) {
                return true;
            }

            ordemDeServico.setStatus(statusConvertido);
            ordemDeServicoRepository.save(ordemDeServico);

            publicarEventoDeStatusAlterado(ordemDeServico, statusAnterior, statusConvertido);
            return true;
        } catch (IllegalArgumentException e) {
            throw new Exception("Status inválido: " + novoStatus + ". Os valores permitidos são: EM_ABERTO, EM_ANDAMENTO, FINALIZADA.");
        }
    }

    @Override
    public boolean finalizarOrdemDeServico(Long id) throws Exception {
        Optional<OrdemDeServicoEntity> osOptional = ordemDeServicoRepository.findById(id);

        if (osOptional.isEmpty()) {
            throw new Exception("Ordem de Serviço não encontrada com o ID: " + id);
        }

        OrdemDeServicoEntity ordemDeServico = osOptional.get();

        try {
            OrdemDeServicoEntity.Status statusAnterior = ordemDeServico.getStatus();
            OrdemDeServicoEntity.Status statusNovo = OrdemDeServicoEntity.Status.FINALIZADA;

            if (statusAnterior == statusNovo) {
                return true;
            }

            ordemDeServico.setStatus(statusNovo);
            ordemDeServicoRepository.save(ordemDeServico);

            publicarEventoDeStatusAlterado(ordemDeServico, statusAnterior, statusNovo);
            return true;
        } catch (Exception e) {
            throw new Exception("Ocorreu um erro ao tentar finalizar a ordem de serviço.\n" + e.getMessage());
        }
    }

    private void publicarEventoDeStatusAlterado(
            OrdemDeServicoEntity ordemDeServico,
            OrdemDeServicoEntity.Status statusAnterior,
            OrdemDeServicoEntity.Status statusNovo
    ) {
        String nomeCliente = "cliente-desconhecido";
        String emailCliente = "email-nao-informado";

        if (ordemDeServico.getVeiculo() != null && ordemDeServico.getVeiculo().getCliente() != null) {
            if (ordemDeServico.getVeiculo().getCliente().getNome() != null) {
                nomeCliente = ordemDeServico.getVeiculo().getCliente().getNome();
            }
            if (ordemDeServico.getVeiculo().getCliente().getEmail() != null) {
                emailCliente = ordemDeServico.getVeiculo().getCliente().getEmail();
            }
        }

        eventPublisher.publishEvent(new OrdemStatusAlteradoEvent(
                ordemDeServico.getId(),
                statusAnterior,
                statusNovo,
                emailCliente,
                nomeCliente
        ));
    }

    @Override
    public boolean removerOrdemDeServico(Long id) throws Exception {
        Optional<OrdemDeServicoEntity> osOptional = ordemDeServicoRepository.findById(id);

        if (osOptional.isEmpty()) {
            throw new Exception("Ordem de Serviço não encontrada com o ID: " + id);
        }

        OrdemDeServicoEntity ordemDeServico = osOptional.get();

        try {
            ordemDeServicoRepository.delete(ordemDeServico);
            return true;
        } catch (Exception e) {
            throw new Exception("Ocorreu um erro ao tentar remover a ordem de serviço.\n" + e.getMessage());
        }
    }
}
