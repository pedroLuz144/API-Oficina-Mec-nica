package com.unifil.oficinaMecanica.async;

import com.unifil.oficinaMecanica.entity.OrdemDeServicoEntity;

public record OrdemStatusAlteradoEvent(
        Long ordemId,
        OrdemDeServicoEntity.Status statusAnterior,
        OrdemDeServicoEntity.Status statusNovo,
        String emailCliente,
        String nomeCliente
) {
}
