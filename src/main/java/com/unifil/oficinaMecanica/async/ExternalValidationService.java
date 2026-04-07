package com.unifil.oficinaMecanica.async;

import com.unifil.oficinaMecanica.entity.VeiculoEntity;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.Random;

@Service
public class ExternalValidationService {

    private static final Logger logger = LoggerFactory.getLogger(ExternalValidationService.class);
    private final Random random = new Random();

    public boolean validarVeiculoComServicoExterno(VeiculoEntity veiculo) throws Exception {
        logger.info("[SERVIÇO EXTERNO] Iniciando validação do veículo com placa: {}", veiculo.getPlaca());

        try {
            Thread.sleep(500 + random.nextInt(1500));
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new Exception("Validação interrompida");
        }

        if (random.nextDouble() < 0.4) {
            logger.error("[SERVIÇO EXTERNO] Falha ao conectar com API externa para validação da placa: {}",
                veiculo.getPlaca());
            throw new Exception("Timeout ao conectar com serviço externo de validação");
        }

        if (veiculo.getPlaca() == null || veiculo.getPlaca().length() < 7) {
            logger.warn("[SERVIÇO EXTERNO] Placa inválida: {}", veiculo.getPlaca());
            return false;
        }

        if (veiculo.getMarca() == null || veiculo.getMarca().isEmpty()) {
            logger.warn("[SERVIÇO EXTERNO] Marca não informada para placa: {}", veiculo.getPlaca());
            return false;
        }

        if (veiculo.getModelo() == null || veiculo.getModelo().isEmpty()) {
            logger.warn("[SERVIÇO EXTERNO] Modelo não informado para placa: {}", veiculo.getPlaca());
            return false;
        }

        logger.info("[SERVIÇO EXTERNO] Veículo validado com sucesso: {} - {} {}",
            veiculo.getPlaca(), veiculo.getMarca(), veiculo.getModelo());
        return true;
    }
}
