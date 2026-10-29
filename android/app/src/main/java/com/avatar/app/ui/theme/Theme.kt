package com.avatar.app.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

val Slate900 = Color(0xFF0F172A)
val Slate800 = Color(0xFF1E293B)
val Slate700 = Color(0xFF334155)
val Slate100 = Color(0xFFF1F5F9)
val Slate50 = Color(0xFFF8FAFC)

val Blue600 = Color(0xFF2563EB)
val Blue500 = Color(0xFF3B82F6)
val Emerald600 = Color(0xFF059669)
val Emerald500 = Color(0xFF10B981)
val Rose600 = Color(0xFFE11D48)
val Rose500 = Color(0xFFF43F5E)
val Amber500 = Color(0xFFF59E0B)

private val LightColorScheme = lightColorScheme(
    primary = Blue600,
    onPrimary = Color.White,
    primaryContainer = Color(0xFFDBEAFE),
    onPrimaryContainer = Color(0xFF1E3A8A),
    secondary = Slate700,
    onSecondary = Color.White,
    background = Slate50,
    surface = Color.White,
    onSurface = Slate900,
    error = Rose600,
    onError = Color.White
)

private val DarkColorScheme = darkColorScheme(
    primary = Blue500,
    onPrimary = Color.White,
    primaryContainer = Color(0xFF1E3A8A),
    onPrimaryContainer = Color(0xFFDBEAFE),
    secondary = Color(0xFF94A3B8),
    onSecondary = Color.Black,
    background = Slate900,
    surface = Slate800,
    onSurface = Slate100,
    error = Rose500,
    onError = Color.White
)

@Composable
fun AvatarAppTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit
) {
    val colorScheme = if (darkTheme) DarkColorScheme else LightColorScheme
    MaterialTheme(
        colorScheme = colorScheme,
        content = content
    )
}
