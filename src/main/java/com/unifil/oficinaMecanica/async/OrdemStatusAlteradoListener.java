package com.unifil.oficinaMecanica.async;

import com.unifil.oficinaMecanica.service.implementacao.NotificacaoStatusOrdemServiceImp;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;

@Component
public class OrdemStatusAlteradoListener {

    @Autowired
    private NotificacaoStatusOrdemServiceImp notificacaoStatusOrdemService;

    @EventListener
    public void onOrdemStatusAlterado(OrdemStatusAlteradoEvent event) {
        notificacaoStatusOrdemService.notificarMudancaDeStatus(event);
    }
}
