package com.unifil.oficinaMecanica.dto.response;

import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
public class LoginResponseDTO {

    private String token;
    private String tipo;
    private String nome;
    private String email;
    private Long expiresIn;

    public LoginResponseDTO(String token, String nome, String email, Long expiresIn) {
        this.token = token;
        this.tipo = "Bearer";
        this.nome = nome;
        this.email = email;
        this.expiresIn = expiresIn;
    }
}
