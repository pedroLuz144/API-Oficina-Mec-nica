package com.unifil.oficinaMecanica.service.implementacao;

import com.unifil.oficinaMecanica.async.OrdemStatusAlteradoEvent;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

@Service
public class NotificacaoStatusOrdemServiceImp {

    private static final Logger LOGGER = LoggerFactory.getLogger(NotificacaoStatusOrdemServiceImp.class);

    @Async("notificacaoTaskExecutor")
    public void notificarMudancaDeStatus(OrdemStatusAlteradoEvent event) {
        try {
            Thread.sleep(1200);
            LOGGER.info(
                    "Notificacao enviada para cliente. OS={}, statusAnterior={}, statusNovo={}, nomeCliente={}, emailCliente={}",
                    event.ordemId(),
                    event.statusAnterior(),
                    event.statusNovo(),
                    event.nomeCliente(),
                    event.emailCliente()
            );
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            LOGGER.error("Thread de notificacao interrompida para OS={}", event.ordemId(), e);
        } catch (Exception e) {
            LOGGER.error("Falha ao processar notificacao de mudanca de status para OS={}", event.ordemId(), e);
        }
    }
}
