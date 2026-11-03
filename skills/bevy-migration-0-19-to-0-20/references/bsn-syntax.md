# BSN syntax changes in Bevy 0.20

BSN (`bsn!`, `bsn_list!`) landed in 0.19. Bevy 0.20 tightened its syntax.

## Scene references take `@`

```rust
// 0.19
bsn! { scene_variable  scene_function()  {scene_expression} }
// 0.20
bsn! { @scene_variable  @scene_function()  @{scene_expression} }
```

## `template_value` is gone

Component values are written directly, including builders and method calls.

```rust
// 0.19
bsn! {
    template_value(Transform::from_xyz(-2.5, 4.5, 9.0).looking_at(Vec3::ZERO, Vec3::Y))
    template_value(node.clone())
}
// 0.20
bsn! {
    Transform::from_xyz(-2.5, 4.5, 9.0).looking_at(Vec3::ZERO, Vec3::Y)
    node.clone()
}
```

## Enums

`VariantDefaults` and `FromTemplate` are no longer required. An enum that is `Default + Clone` works as-is. Per-variant field defaults are gone: every field of a variant must be written, exactly like plain Rust.

```rust
#[derive(Component, Default, Clone)]
enum Foo { A { x: u32, y: u32 }, #[default] B }

bsn! { Foo::A { x: 1, y: 0 } } // 0.19 allowed `Foo::A { x: 1 }`
```

## Entities are separated with `--`

```rust
bsn! {
    Node
    Children [
        #OkButton
        @button("Ok")
        --
        #CancelButton
        @button("Cancel")
    ]
}
```

`()` around entities and `,` between them are deprecated. Prefer `bsn_list! { ... }` with braces; `[]`/`()` fight rustfmt.

Source: https://bevy.org/learn/migration-guides/0-19-to-0-20/ ("BSN syntax improvements").
