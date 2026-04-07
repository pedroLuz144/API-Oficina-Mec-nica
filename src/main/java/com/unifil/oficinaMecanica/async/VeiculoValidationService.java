package com.unifil.oficinaMecanica.async;

import com.unifil.oficinaMecanica.entity.VeiculoEntity;
import com.unifil.oficinaMecanica.repository.VeiculoRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.retry.annotation.Backoff;
import org.springframework.retry.annotation.Recover;
import org.springframework.retry.annotation.Retryable;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

@Service
public class VeiculoValidationService {

    private static final Logger logger = LoggerFactory.getLogger(VeiculoValidationService.class);

    @Autowired
    private ExternalValidationService externalValidationService;

    @Autowired
    private VeiculoRepository veiculoRepository;

    @Async("veiculoValidationExecutor")
    @Retryable(
        retryFor = { Exception.class },
        maxAttempts = 3,
        backoff = @Backoff(delay = 2000, multiplier = 2)
    )
    public void validarVeiculoAssincronamente(String placa) throws Exception {
        String timestamp = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"));
        String threadName = Thread.currentThread().getName();

        logger.info("╔══════════════════════════════════════════════════════════════════╗");
        logger.info("║ [VALIDAÇÃO ASSÍNCRONA] Iniciando validação                      ║");
        logger.info("║ Placa: {}                                              ║", placa);
        logger.info("║ Thread: {}                              ║", threadName);
        logger.info("║ Timestamp: {}                                   ║", timestamp);
        logger.info("╚══════════════════════════════════════════════════════════════════╝");

        try {
            VeiculoEntity veiculo = veiculoRepository.findById(placa)
                .orElseThrow(() -> new Exception("Veículo não encontrado: " + placa));

            logger.info("[VALIDAÇÃO ASSÍNCRONA] Veículo encontrado: {} - {} {}",
                veiculo.getPlaca(), veiculo.getMarca(), veiculo.getModelo());

            boolean validado = externalValidationService.validarVeiculoComServicoExterno(veiculo);

            if (validado) {
                logger.info("╔══════════════════════════════════════════════════════════════════╗");
                logger.info("║ [VALIDAÇÃO ASSÍNCRONA] ✓ SUCESSO                               ║");
                logger.info("║ Placa: {}                                              ║", placa);
                logger.info("║ Status: Validado com sucesso                                    ║");
                logger.info("║ Thread: {}                              ║", threadName);
                logger.info("╚══════════════════════════════════════════════════════════════════╝");
            } else {
                logger.warn("╔══════════════════════════════════════════════════════════════════╗");
                logger.warn("║ [VALIDAÇÃO ASSÍNCRONA] ⚠ FALHA NA VALIDAÇÃO                    ║");
                logger.warn("║ Placa: {}                                              ║", placa);
                logger.warn("║ Status: Dados inválidos detectados pelo serviço externo         ║");
                logger.warn("║ Thread: {}                              ║", threadName);
                logger.warn("╚══════════════════════════════════════════════════════════════════╝");
            }

        } catch (Exception e) {
            logger.error("╔══════════════════════════════════════════════════════════════════╗");
            logger.error("║ [VALIDAÇÃO ASSÍNCRONA] ✗ ERRO                                  ║");
            logger.error("║ Placa: {}                                              ║", placa);
            logger.error("║ Erro: {}                                                ║", e.getMessage());
            logger.error("║ Thread: {}                              ║", threadName);
            logger.error("║ Ação: Tentando novamente (retry automático)...                  ║");
            logger.error("╚══════════════════════════════════════════════════════════════════╝");
            throw e;
        }
    }

    @Recover
    public void recuperarValidacaoFalha(Exception e, String placa) {
        String timestamp = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"));
        String threadName = Thread.currentThread().getName();

        logger.error("╔══════════════════════════════════════════════════════════════════╗");
        logger.error("║ [VALIDAÇÃO ASSÍNCRONA] ✗ FALHA APÓS TODAS AS TENTATIVAS        ║");
        logger.error("║ Placa: {}                                              ║", placa);
        logger.error("║ Tentativas: 3/3 (máximo atingido)                               ║");
        logger.error("║ Erro Final: {}                                          ║", e.getMessage());
        logger.error("║ Thread: {}                              ║", threadName);
        logger.error("║ Timestamp: {}                                   ║", timestamp);
        logger.error("║                                                                  ║");
        logger.error("║ Ação Necessária:                                                ║");
        logger.error("║ - Verificar conectividade com serviço externo                   ║");
        logger.error("║ - Validar manualmente o veículo                                 ║");
        logger.error("║ - Verificar logs do serviço externo                             ║");
        logger.error("╚══════════════════════════════════════════════════════════════════╝");
    }
}
